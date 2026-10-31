from datetime import datetime, date, timedelta
from typing import List, Dict
from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.session import get_database
from app.api.dependencies import get_current_merchant
from app.schemas.dashboard import (
    DashboardSummaryResponse, StockWarningItem, GrowthRecommendation, ActionRecommendationItem
)
from app.schemas.sales import DailySaleRecord
from app.schemas.forecast import DailyForecastPoint
from app.services.forecasting import forecasting_service, load_relevant_events
from app.services.action_guards import max_discount_above_cost

router = APIRouter(prefix="/dashboard", tags=["Merchant Dashboard"])

@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    merchant: dict = Depends(get_current_merchant),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Consolidated merchant dashboard summary:
    - 30d indicators (revenue, orders, growth score)
    - 30d historical sales trend
    - 7-day demand forecast aggregation
    - Critical stock warnings
    - One prioritized growth recommendation
    """
    m_id = merchant["merchant_id"]
    today = date.today()
    start_30d = (today - timedelta(days=30)).strftime("%Y-%m-%d")
    start_60d = (today - timedelta(days=60)).strftime("%Y-%m-%d")

    # Fetch products
    products = await db.products.find({"merchant_id": m_id}).to_list(length=100)

    # Fetch 30-day and prior 30-day sales
    recent_sales = await db.sales.find({
        "merchant_id": m_id,
        "date": {"$gte": start_30d}
    }).sort("date", 1).to_list(length=1000)

    prior_sales = await db.sales.find({
        "merchant_id": m_id,
        "date": {"$gte": start_60d, "$lt": start_30d}
    }).to_list(length=1000)

    total_rev_30d = sum(float(s.get("revenue", 0.0)) for s in recent_sales)
    total_rev_prior = sum(float(s.get("revenue", 0.0)) for s in prior_sales)
    total_units_30d = sum(int(s.get("units_sold", 0)) for s in recent_sales)

    rev_growth_pct = round(
        ((total_rev_30d - total_rev_prior) / total_rev_prior * 100.0), 1
    ) if total_rev_prior > 0 else 12.4

    # Daily aggregation for the sales history chart
    daily_map: Dict[str, Dict[str, float]] = {}
    for s in recent_sales:
        d = s["date"]
        if d not in daily_map:
            daily_map[d] = {"revenue": 0.0, "units": 0, "cogs": 0.0, "profit": 0.0}
        daily_map[d]["revenue"] += float(s.get("revenue", 0.0))
        daily_map[d]["units"] += int(s.get("units_sold", 0))
        daily_map[d]["cogs"] += float(s.get("cogs", 0.0))
        daily_map[d]["profit"] += float(s.get("gross_profit", 0.0))

    sales_history_30d = [
        DailySaleRecord(
            date=d,
            units_sold=val["units"],
            revenue=round(val["revenue"], 2),
            cogs=round(val["cogs"], 2),
            gross_profit=round(val["profit"], 2),
        )
        for d, val in sorted(daily_map.items())
    ]

    total_orders = sum(val["units"] for val in daily_map.values())
    avg_order_val = round(total_rev_30d / len(daily_map), 2) if daily_map else 0.0

    # Stock warnings & 7-day forecast aggregation
    stock_warnings: List[StockWarningItem] = []
    day_forecast_totals: Dict[str, int] = {}
    day_forecast_rev: Dict[str, float] = {}
    day_names_map: Dict[str, str] = {}
    product_evaluations = []
    events = await load_relevant_events(db, merchant)

    for p in products:
        p_sales = [s for s in recent_sales if s.get("product_id") == p["product_id"]]
        fc = forecasting_service.forecast_product(
            p, p_sales, horizon_days=7,
            events=events, merchant_category=merchant.get("category"),
        )
        curr_stock = int(p.get("current_stock", 0))
        reorder_th = int(p.get("reorder_threshold", 10))
        cost_p = float(p.get("cost_price", 0.0))
        sell_p = float(p.get("selling_price", 0.0))

        product_evaluations.append({
            "product_id": p["product_id"],
            "name": p["name"],
            "category": p.get("category", "General"),
            "current_stock": curr_stock,
            "reorder_threshold": reorder_th,
            "cost_price": cost_p,
            "selling_price": sell_p,
            "days_of_stock_left": fc.days_of_inventory_remaining,
            "forecast": fc,
            "stockout_risk": fc.stockout_risk or (curr_stock <= reorder_th),
        })

        # Aggregate daily points for the forecast summary
        for pt in fc.daily_forecasts:
            day_forecast_totals[pt.date] = day_forecast_totals.get(pt.date, 0) + pt.predicted_units
            day_forecast_rev[pt.date] = day_forecast_rev.get(pt.date, 0.0) + pt.projected_revenue
            day_names_map[pt.date] = pt.day_name

        # Check stock warning
        if fc.stockout_risk or curr_stock <= reorder_th:
            severity = "CRITICAL" if curr_stock <= (reorder_th // 2) else "WARNING"
            stock_warnings.append(
                StockWarningItem(
                    product_id=p["product_id"],
                    product_name=p["name"],
                    category=p.get("category", "General"),
                    current_stock=curr_stock,
                    reorder_threshold=reorder_th,
                    days_of_stock_left=fc.days_of_inventory_remaining,
                    recommended_reorder=fc.recommended_replenishment_units or (reorder_th * 2),
                    severity=severity,
                )
            )

    seven_day_summary = [
        DailyForecastPoint(
            date=d,
            day_name=day_names_map.get(d, "Day"),
            predicted_units=day_forecast_totals[d],
            projected_revenue=round(day_forecast_rev[d], 2),
            is_weekend=(d in day_names_map and day_names_map[d] in ("Saturday", "Sunday")),
        )
        for d in sorted(day_forecast_totals.keys())
    ]

    # Calculate growth health score (0-100)
    low_stock_penalty = len(stock_warnings) * 8
    growth_health_score = max(40, min(95, 82 - low_stock_penalty + int(min(rev_growth_pct, 15))))

    # Build Top Recommendations in 3 explicit categories:
    # 1. Most important product to be restocked due to low stock
    # 2. Most recommended product to be kept on discount (Excess / Overstocked stock clearance)
    # 3. Most recommended product to add discount (lowest stock) with minimum required discount
    top_recommendations: List[ActionRecommendationItem] = []

    # 1. Restock Priority: Lowest runway / critical stockout risk
    critical_candidates = sorted(
        product_evaluations,
        key=lambda x: (0 if x["stockout_risk"] else 1, x["days_of_stock_left"])
    )
    top_restock = critical_candidates[0] if critical_candidates else None

    if top_restock:
        reorder_units = top_restock["forecast"].recommended_replenishment_units or (top_restock["reorder_threshold"] * 2)
        margin = max(10.0, top_restock["selling_price"] - top_restock["cost_price"])
        restock_lift = round(reorder_units * margin, 2)
        top_recommendations.append(
            ActionRecommendationItem(
                recommendation_id="rec-restock-priority-01",
                category_type="RESTOCK_PRIORITY",
                badge_label="Restock Priority",
                title=f"Replenish '{top_restock['name']}'",
                product_id=top_restock["product_id"],
                product_name=top_restock["name"],
                current_stock=top_restock["current_stock"],
                metric_highlight=f"Only {top_restock['days_of_stock_left']} days runway remaining",
                summary=f"Stock for '{top_restock['name']}' is critically depleted ({top_restock['current_stock']} units on hand against threshold of {top_restock['reorder_threshold']}). Reorder {reorder_units} units.",
                rationale="High sales velocity during upcoming peak days will face stockout if unreplenished, permanently losing sales to neighboring stores.",
                recommended_quantity=reorder_units,
                projected_revenue_lift=restock_lift if restock_lift > 0 else 2400.0,
                action_type="RESTOCK_PRODUCT",
                action_url="/demand",
            )
        )

    # 2. Excess Clearance Discount: Product with highest inventory runway / slowest turnover
    excess_candidates = [
        p for p in product_evaluations
        if (not top_restock or p["product_id"] != top_restock["product_id"]) and p["current_stock"] > 0
    ]
    excess_candidates.sort(key=lambda x: x["days_of_stock_left"], reverse=True)

    # Recommended discounts must never price a product below cost (they prefill the
    # campaign popup). Keep ~3 percentage points of margin as a buffer.
    def safe_discount_cap(p: dict) -> float:
        return max_discount_above_cost({"selling_price": p["selling_price"], "cost_price": p["cost_price"]}) - 3.0

    top_excess = next((p for p in excess_candidates if safe_discount_cap(p) >= 3.0), None)
    clearance_pct = min(12.0, safe_discount_cap(top_excess)) if top_excess else 0.0

    if top_excess:
        excess_lift = round(top_excess["selling_price"] * min(top_excess["current_stock"], 20) * (1 - clearance_pct / 100.0), 2)
        top_recommendations.append(
            ActionRecommendationItem(
                recommendation_id="rec-clearance-discount-02",
                category_type="CLEARANCE_DISCOUNT",
                badge_label="Excess Clearance",
                title=f"Discount '{top_excess['name']}' (Clear Stock)",
                product_id=top_excess["product_id"],
                product_name=top_excess["name"],
                current_stock=top_excess["current_stock"],
                metric_highlight=f"Surplus stock (~{int(top_excess['days_of_stock_left'])} days supply)",
                summary=f"Holding {top_excess['current_stock']} units of '{top_excess['name']}' with slow turnover. A {clearance_pct:g}% clearance discount will accelerate stock velocity.",
                rationale="Liquidating surplus slow-moving stock releases capital to reinvest into fast-turning daily essentials.",
                suggested_discount_pct=clearance_pct,
                projected_revenue_lift=excess_lift if excess_lift > 0 else 3200.0,
                action_type="CREATE_CAMPAIGN",
                action_url="/campaigns",
            )
        )

    # 3. Minimum Margin Discount: Lowest stock candidate among remaining with minimal required discount
    min_discount_candidates = [
        p for p in product_evaluations
        if (not top_restock or p["product_id"] != top_restock["product_id"])
        and (not top_excess or p["product_id"] != top_excess["product_id"])
        and p["current_stock"] > 0
    ]
    if not min_discount_candidates:
        min_discount_candidates = [p for p in product_evaluations if not top_restock or p["product_id"] != top_restock["product_id"]]

    min_discount_candidates.sort(key=lambda x: x["current_stock"])
    top_min_discount = next((p for p in min_discount_candidates if safe_discount_cap(p) >= 2.0), None)

    if top_min_discount:
        sp = top_min_discount["selling_price"]
        cp = top_min_discount["cost_price"]
        margin_pct = ((sp - cp) / sp * 100.0) if sp > 0 else 20.0
        min_discount_val = 5.0 if margin_pct >= 22.0 else (6.0 if margin_pct >= 15.0 else 4.0)
        min_discount_val = float(int(min(min_discount_val, safe_discount_cap(top_min_discount))))
        promo_price = sp * (1.0 - min_discount_val / 100.0)
        margin_after = ((promo_price - cp) / promo_price * 100.0) if promo_price > 0 else 0.0
        min_lift = round(sp * top_min_discount["current_stock"] * (1.0 - min_discount_val / 100.0), 2)

        top_recommendations.append(
            ActionRecommendationItem(
                recommendation_id="rec-min-margin-discount-03",
                category_type="MIN_MARGIN_DISCOUNT",
                badge_label="Min. Margin Promo",
                title=f"Add Minimal {int(min_discount_val)}% Discount on '{top_min_discount['name']}'",
                product_id=top_min_discount["product_id"],
                product_name=top_min_discount["name"],
                current_stock=top_min_discount["current_stock"],
                metric_highlight=f"Min. {int(min_discount_val)}% discount needed ({top_min_discount['current_stock']} units batch)",
                summary=f"Lowest stock candidate ({top_min_discount['current_stock']} units on hand). A minimal {int(min_discount_val)}% discount triggers buying urgency while keeping {int(margin_after)}% gross margin intact.",
                rationale="Applying the smallest effective price reduction drives immediate sell-through of the remaining batch without eroding store profitability.",
                suggested_discount_pct=min_discount_val,
                projected_revenue_lift=min_lift if min_lift > 0 else 1800.0,
                action_type="CREATE_CAMPAIGN",
                action_url="/campaigns",
            )
        )

    # Legacy fallback field
    legacy_rec = None
    if top_recommendations:
        primary = top_recommendations[0]
        legacy_rec = GrowthRecommendation(
            recommendation_id=primary.recommendation_id,
            title=primary.title,
            category=primary.category_type,
            summary=primary.summary,
            rationale=primary.rationale,
            projected_revenue_lift=primary.projected_revenue_lift,
            confidence_level="HIGH",
            action_type=primary.action_type,
            action_payload={
                "product_id": primary.product_id,
                "product_name": primary.product_name,
                "quantity": primary.recommended_quantity or 20,
            },
        )

    return DashboardSummaryResponse(
        merchant_id=m_id,
        business_name=merchant["business_name"],
        category=merchant.get("category", "Retail"),
        total_revenue_30d=round(total_rev_30d, 2),
        revenue_growth_pct=rev_growth_pct,
        total_orders_30d=total_orders,
        avg_order_value=avg_order_val,
        low_stock_items_count=len(stock_warnings),
        growth_health_score=growth_health_score,
        sales_history_30d=sales_history_30d,
        seven_day_forecast_summary=seven_day_summary,
        stock_warnings=stock_warnings,
        prioritized_growth_recommendation=legacy_rec,
        top_recommendations=top_recommendations,
    )
