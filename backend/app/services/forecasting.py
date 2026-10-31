import asyncio
import logging
import re
import time
from datetime import date, timedelta
from typing import List, Dict, Optional, Tuple
from app.schemas.forecast import DailyForecastPoint, ProductForecastResponse

logger = logging.getLogger(__name__)

ALL_CATEGORIES = "all categories"

# Festivals come from the same All-India occasions feed as the Events page
# (services/occasions.py). Only major festivals (severity HIGH, e.g. Diwali, Eid, Holi)
# adjust forecasts: the calendar also lists many minor observances, and boosting every
# one of them would inflate forecasts most days of the year.
FORECAST_EVENT_SEVERITIES = {"HIGH"}
# Don't let a slow or unreachable calendar slow down the dashboard / demand / copilot:
OCCASIONS_TIMEOUT_SECONDS = 3.0
OCCASIONS_RETRY_AFTER_SECONDS = 600  # after a failure, skip festivals for 10 minutes
_occasions_failed_at: float = 0.0

# Words too generic to link a festival impact to a product ("Retail Footfall", "Gift Boxes" ...)
_GENERIC_WORDS = {
    "and", "the", "retail", "footfall", "festive", "festival", "general", "store", "stores",
    "item", "items", "product", "products", "daily", "essential", "essentials", "special",
    "all", "category", "categories", "gifting", "gift", "box", "pack", "mix", "kit",
    "premium", "pure", "seasonal", "convenience", "packaged", "local",
}


def _stem(word: str) -> str:
    """Simple singular form: groceries->grocery, sweets->sweet, beverages->beverage."""
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


# Two-word terms that mean something different from their parts
# ("Dry Fruits" are nuts like almonds and cashews, not fresh fruit)
_COMPOUND_TERMS = [(re.compile(r"\bdry\s+fruits?\b"), "dryfruit")]


def _key_words(text: Optional[str]) -> set:
    t = (text or "").lower()
    for pattern, token in _COMPOUND_TERMS:
        t = pattern.sub(token, t)
    return {
        _stem(w) for w in re.findall(r"[a-z]+", t)
        if len(w) >= 3 and _stem(w) not in _GENERIC_WORDS
    }


async def load_relevant_events(db, merchant: dict) -> List[dict]:
    """
    Major upcoming festivals for forecasting, from the same All-India occasions feed
    the Events page uses. Load once per request and pass to forecast_product(events=...).
    Returns [] (no festival adjustment) if the feed is slow or unavailable.
    """
    global _occasions_failed_at
    if time.time() - _occasions_failed_at < OCCASIONS_RETRY_AFTER_SECONDS:
        return []
    try:
        from app.services.occasions import get_all_india_occasions
        lat = merchant.get("latitude")
        lng = merchant.get("longitude")
        kwargs = {"merchant": None, "merchant_category": merchant.get("category", ""), "db": None}
        if lat is not None and lng is not None:
            kwargs.update(merchant_lat=float(lat), merchant_lng=float(lng))
        # merchant=None -> base festival rules only (no per-request Gemini call); the feed is cached
        events, _source = await asyncio.wait_for(
            get_all_india_occasions(**kwargs), timeout=OCCASIONS_TIMEOUT_SECONDS
        )
    except Exception as e:  # timeout, network error, unexpected data
        logger.warning(f"Festival feed unavailable for forecasting ({e!r}); forecasting without festivals.")
        _occasions_failed_at = time.time()
        return []
    if not events:
        _occasions_failed_at = time.time()
        return []

    today_str = date.today().isoformat()
    relevant = []
    for ev in events:
        d = ev.model_dump() if hasattr(ev, "model_dump") else dict(ev)
        if (d.get("end_date") or d.get("start_date") or "") < today_str:
            continue
        if (d.get("severity") or "").upper() not in FORECAST_EVENT_SEVERITIES:
            continue
        relevant.append(d)
    return relevant


def event_multiplier_for_day(
    target_date: date,
    product_category: str,
    merchant_category: Optional[str],
    events: Optional[List[dict]],
) -> Tuple[float, Optional[str]]:
    """
    Demand multiplier from festivals active on target_date.
    A festival impact applies to a product when its category shares a key word with the
    product's or merchant's category ("Dry Fruits & Groceries" ~ "Grocery & Daily Essentials",
    "Beverages & Dairy" ~ "Dairy"), or when it is "All Categories".
    Highlighted product names are deliberately NOT matched: single words like "oil" would
    link Holi's skin-care "Coconut Oil" to cooking oil.
    Overlapping festivals don't stack: the strongest one is used, to avoid runaway forecasts.
    """
    if not events:
        return 1.0, None
    day = target_date.strftime("%Y-%m-%d")
    category_words = _key_words(product_category) | _key_words(merchant_category)

    best_mult, best_title = 1.0, None
    for ev in events:
        start = ev.get("start_date") or ""
        end = ev.get("end_date") or start
        if not (start <= day <= end):
            continue
        for impact in ev.get("category_impacts") or []:
            cat = (impact.get("category") or "").strip().lower()
            matches = cat == ALL_CATEGORIES or bool(_key_words(cat) & category_words)
            if not matches:
                continue
            try:
                mult = float(impact.get("multiplier", 1.0))
            except (TypeError, ValueError):
                continue
            if mult > best_mult:
                best_mult, best_title = mult, ev.get("title")
    return best_mult, best_title

class DemandForecastingService:
    """
    Transparent, interpretable historical baseline forecasting service.
    Engineered as an isolated service class so a scikit-learn or ARIMA model
    can implement the same interface seamlessly.
    """

    def forecast_product(
        self,
        product: dict,
        sales_history: List[dict],
        horizon_days: int = 7,
        events: Optional[List[dict]] = None,
        merchant_category: Optional[str] = None,
    ) -> ProductForecastResponse:
        """
        Produce a 7-day demand forecast for a single product using a weekday-aware
        historical weighted moving average.
        """
        product_id = product["product_id"]
        product_name = product["name"]
        category = product.get("category", "General")
        current_stock = int(product.get("current_stock", 0))
        reorder_threshold = int(product.get("reorder_threshold", 10))
        selling_price = float(product.get("selling_price", 0.0))
        effective_selling_price = float(product.get("effective_selling_price", selling_price))
        is_promotional = effective_selling_price < (selling_price - 0.01)

        # Promotional demand elasticity factor
        if is_promotional and selling_price > 0:
            discount_pct = round(((selling_price - effective_selling_price) / selling_price) * 100.0, 1)
            # Price elasticity: e.g. 10% discount boosts expected unit velocity by 15%
            promo_multiplier = 1.0 + (discount_pct / 100.0) * 1.5
        else:
            discount_pct = 0.0
            promo_multiplier = 1.0

        # Sort sales history by date ascending
        sorted_history = sorted(sales_history, key=lambda s: s["date"])
        total_days_available = len(sorted_history)

        # Evaluate data sufficiency
        sufficiency_warning = None
        if total_days_available < 14:
            sufficiency_warning = (
                f"Limited historical window: only {total_days_available} days recorded. "
                "Forecast relies on limited sample mean; recommend at least 28 days for seasonal fidelity."
            )
            historical_window_days = total_days_available
        elif total_days_available < 28:
            sufficiency_warning = (
                f"Moderate history: {total_days_available} days recorded. "
                "Baseline uses 14-day recency weighting without multi-month cyclical adjustment."
            )
            historical_window_days = total_days_available
        else:
            historical_window_days = min(90, total_days_available)

        # Compute weekday-specific historical averages
        # Map 0..6 (Mon..Sun) -> list of units_sold
        weekday_buckets: Dict[int, List[int]] = {i: [] for i in range(7)}
        for sale in sorted_history[-historical_window_days:]:
            try:
                sale_date = date.fromisoformat(sale["date"])
                weekday_buckets[sale_date.weekday()].append(int(sale.get("units_sold", 0)))
            except (ValueError, TypeError):
                continue

        # Global average fallback
        all_recent_units = [int(s.get("units_sold", 0)) for s in sorted_history[-historical_window_days:]]
        global_avg = (sum(all_recent_units) / len(all_recent_units)) if all_recent_units else 5.0

        today = date.today()
        daily_forecasts: List[DailyForecastPoint] = []
        total_forecasted_units = 0
        event_days: List[Tuple[str, float, str]] = []  # (day_name, multiplier, event title)
        baseline_units_no_events = 0.0  # same forecast without event uplift (for replenishment)

        # Day names
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        for i in range(1, horizon_days + 1):
            target_date = today + timedelta(days=i)
            target_weekday = target_date.weekday()
            is_weekend = target_weekday in (5, 6)

            samples = weekday_buckets[target_weekday]
            if len(samples) >= 2:
                # Weighted recent average: last 2 occurrences receive 60% weight, older 40%
                if len(samples) >= 4:
                    recent_weights = samples[-2:]
                    older_weights = samples[:-2]
                    recent_mean = sum(recent_weights) / len(recent_weights)
                    older_mean = sum(older_weights) / len(older_mean_samples := older_weights)
                    pred_float = (recent_mean * 0.65) + (older_mean * 0.35)
                else:
                    pred_float = sum(samples) / len(samples)
            elif samples:
                pred_float = (samples[-1] * 0.5) + (global_avg * 0.5)
            else:
                pred_float = global_avg

            # Apply promotional elasticity multiplier if active campaign is running
            pred_float = pred_float * promo_multiplier

            # Apply neighbourhood event uplift (festivals, fairs, match screenings, ...)
            baseline_units_no_events += max(1.0, pred_float)
            ev_mult, ev_title = event_multiplier_for_day(target_date, category, merchant_category, events)
            if ev_mult != 1.0:
                pred_float = pred_float * ev_mult
                event_days.append((day_names[target_weekday], ev_mult, ev_title))

            predicted_units = max(1, int(round(pred_float)))
            projected_rev = round(predicted_units * effective_selling_price, 2)
            total_forecasted_units += predicted_units

            daily_forecasts.append(
                DailyForecastPoint(
                    date=target_date.strftime("%Y-%m-%d"),
                    day_name=day_names[target_weekday],
                    predicted_units=predicted_units,
                    projected_revenue=projected_rev,
                    is_weekend=is_weekend,
                    event_multiplier=round(ev_mult, 2),
                    event_title=ev_title,
                )
            )

        total_projected_revenue = round(total_forecasted_units * effective_selling_price, 2)

        # Inventory runway and stockout risk calculations
        avg_daily_demand = total_forecasted_units / horizon_days if horizon_days > 0 else 1.0
        days_of_inventory = round(current_stock / avg_daily_demand, 1) if avg_daily_demand > 0 else 99.0
        
        # Stockout risk is True if current stock will be exhausted before the 7-day horizon or is below reorder threshold
        stockout_risk = (current_stock < total_forecasted_units) or (current_stock <= reorder_threshold)
        
        # Recommended replenishment: stock for 14 days of demand + reorder-threshold buffer.
        # The forecast window uses the event-adjusted forecast; the days after it use normal
        # (no-event) demand, so a short festival spike isn't stretched across two weeks.
        # Without events this equals the original "avg daily demand x 14 + threshold" rule.
        coverage_days = 14
        if horizon_days >= coverage_days:
            demand_to_cover = avg_daily_demand * coverage_days
        else:
            normal_daily = baseline_units_no_events / horizon_days if horizon_days > 0 else 0.0
            demand_to_cover = total_forecasted_units + normal_daily * (coverage_days - horizon_days)
        target_stock_level = int(round(demand_to_cover)) + reorder_threshold
        replenishment = max(0, target_stock_level - current_stock)

        method_str = "Weekday-Stratified Weighted Historical Baseline (7-Day)"
        if event_days:
            method_str += " + Festival Adjustment"
        if is_promotional:
            explanation = (
                f"Active promotion ({discount_pct}% off) in effect at ₹{effective_selling_price} (Regular: ₹{selling_price}). "
                f"Demand elasticity (+{int((promo_multiplier - 1.0) * 100)}% velocity) factored into 7-day consumption ({total_forecasted_units} units). "
                f"At stock of {current_stock}, estimated promotional runway is {days_of_inventory} days."
            )
        else:
            explanation = (
                f"Based on {historical_window_days} days of product-level transaction history. "
                f"Expected 7-day consumption is {total_forecasted_units} {product.get('unit', 'units')}. "
                f"At current stock of {current_stock}, estimated runway is {days_of_inventory} days."
            )

        if event_days:
            titles = sorted({t for _, _, t in event_days if t})
            peak = max(m for _, m, _ in event_days)
            explanation += (
                f" Includes festival uplift on {len(event_days)} day(s) "
                f"(up to {peak:g}x) from: {', '.join(titles)}."
            )

        return ProductForecastResponse(
            product_id=product_id,
            product_name=product_name,
            category=category,
            current_stock=current_stock,
            reorder_threshold=reorder_threshold,
            selling_price=selling_price,
            effective_selling_price=effective_selling_price,
            is_promotional=is_promotional,
            daily_forecasts=daily_forecasts,
            total_forecasted_units=total_forecasted_units,
            total_projected_revenue=total_projected_revenue,
            method_used=method_str,
            historical_window_days=historical_window_days,
            data_sufficiency_warning=sufficiency_warning,
            days_of_inventory_remaining=days_of_inventory,
            stockout_risk=stockout_risk,
            recommended_replenishment_units=replenishment,
            explanation=explanation,
        )

forecasting_service = DemandForecastingService()
