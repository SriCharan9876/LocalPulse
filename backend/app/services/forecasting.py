from datetime import date, timedelta
from typing import List, Dict, Optional, Tuple
from app.schemas.forecast import DailyForecastPoint, ProductForecastResponse

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
        horizon_days: int = 7
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
                )
            )

        total_projected_revenue = round(total_forecasted_units * effective_selling_price, 2)

        # Inventory runway and stockout risk calculations
        avg_daily_demand = total_forecasted_units / horizon_days if horizon_days > 0 else 1.0
        days_of_inventory = round(current_stock / avg_daily_demand, 1) if avg_daily_demand > 0 else 99.0
        
        # Stockout risk is True if current stock will be exhausted before the 7-day horizon or is below reorder threshold
        stockout_risk = (current_stock < total_forecasted_units) or (current_stock <= reorder_threshold)
        
        # Recommended replenishment units: bring stock to 14 days of demand + safety buffer of reorder threshold
        target_stock_level = int(round(avg_daily_demand * 14)) + reorder_threshold
        replenishment = max(0, target_stock_level - current_stock)

        method_str = "Weekday-Stratified Exponentially Weighted Historical Baseline (7-Day)"
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
