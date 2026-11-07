"""
Forecasting execution mixin for Copilot Agent tools:
- get_demand_forecast
"""

from typing import List, Optional, Any
from app.schemas.copilot import (
    CopilotChatResponse, CopilotEvidenceItem, ChartData, ChartPoint,
)
from app.services.forecasting import forecasting_service


class ForecastingExecutorMixin:
    """Handles forward-looking demand forecasting and stockout risk analysis."""

    # ── Tool: get_demand_forecast ───────────────────────────────────────────
    async def execute_get_demand_forecast(
        self,
        args: dict,
        merchant: dict,
        products: List[dict],
        sales: List[dict],
        events: Optional[List[dict]] = None,
        db: Any = None,
    ) -> CopilotChatResponse:
        """Tool: get_demand_forecast"""
        p_name = (args.get("product_name") or "").strip().lower()
        days = int(args.get("days") or 7)
        days = max(1, min(14, days))

        target_p = None
        if p_name and p_name not in ["all", "store", "everything"]:
            target_p = self.find_product_by_name(p_name, products)
            if not target_p:
                return self._product_not_found(p_name, products, "get_demand_forecast", "forecast demand for")

        m_cat = merchant.get("category", "")

        if target_p:
            p_id = target_p["product_id"]
            p_sales = [s for s in sales if s.get("product_id") == p_id]
            fc = forecasting_service.forecast_product(
                product=target_p,
                sales=p_sales,
                horizon_days=days,
                events=events,
                merchant_category=m_cat,
            )

            lines = [
                f"**{days}-Day Demand Forecast: {target_p['name']}**\n",
                f"- **Current Stock:** {target_p.get('current_stock', 0)} units (Reorder threshold: {target_p.get('reorder_threshold', 10)})",
                f"- **Projected Demand:** **{fc.total_forecasted_units} units** over the next {days} days",
                f"- **Projected Revenue:** **₹{fc.total_projected_revenue:,.2f}**",
                f"- **Average Daily Pace:** {fc.avg_daily_projected_units:.1f} units/day",
            ]

            if fc.stockout_risk:
                diff = fc.total_forecasted_units - int(target_p.get("current_stock", 0))
                lines.append(f"\n⚠️ **Stockout Risk Alert:** Current stock will be depleted before day {days}. Projected shortfall: **{diff} units**. Restock recommended!")
            else:
                lines.append(f"\n✅ **Stock Runway Healthy:** Projected demand is safely covered by current inventory.")

            chart_points = []
            for d in fc.daily_forecasts:
                chart_points.append(ChartPoint(
                    label=d.day_of_week[:3],
                    value=float(d.forecasted_units),
                    full_label=f"{d.date} ({d.day_of_week}): {d.forecasted_units} units"
                ))

            chart = ChartData(
                kind="columns",
                title=f"{days}-Day Demand Forecast: {target_p['name']}",
                value_label="Projected Units",
                points=chart_points,
                auto_open=True,
            )

            evidence = [
                CopilotEvidenceItem(source_metric="Forecast Horizon", value=f"{days} days", context="Weekday baseline + event uplift"),
                CopilotEvidenceItem(source_metric="Projected Units", value=f"{fc.total_forecasted_units} units", context=f"₹{fc.total_projected_revenue:,.0f} revenue"),
                CopilotEvidenceItem(source_metric="Stockout Risk", value="HIGH" if fc.stockout_risk else "NONE", context=f"Current: {target_p.get('current_stock', 0)} units"),
            ]

            return CopilotChatResponse(
                reply="\n".join(lines).strip(),
                evidence=evidence,
                draft_action=None,
                chart=chart,
                llm_configured=True,
                provider_info="LocalPulse Agent Tool: get_demand_forecast",
            )
        else:
            forecasts = []
            total_units = 0
            total_rev = 0.0
            stockout_count = 0

            for p in products:
                p_id = p["product_id"]
                p_sales = [s for s in sales if s.get("product_id") == p_id]
                fc = forecasting_service.forecast_product(
                    product=p,
                    sales=p_sales,
                    horizon_days=days,
                    events=events,
                    merchant_category=m_cat,
                )
                forecasts.append((p, fc))
                total_units += fc.total_forecasted_units
                total_rev += fc.total_projected_revenue
                if fc.stockout_risk:
                    stockout_count += 1

            forecasts.sort(key=lambda x: x[1].total_forecasted_units, reverse=True)

            lines = [
                f"**Store-Wide {days}-Day Demand Forecast Summary**\n",
                f"- **Products Analyzed:** {len(products)} catalog items",
                f"- **Total Projected Units:** **{total_units} units**",
                f"- **Total Projected Revenue:** **₹{total_rev:,.2f}**",
                f"- **High Stockout Risk Items:** **{stockout_count} products**",
                "",
                "### Top Projected Products:"
            ]

            chart_points = []
            for i, (p, fc) in enumerate(forecasts[:5], 1):
                risk_tag = "⚠️ *Stockout Risk*" if fc.stockout_risk else "✅ *Safe*"
                lines.append(f"{i}. **{p['name']}**: **{fc.total_forecasted_units} units** (₹{fc.total_projected_revenue:,.0f}) — {risk_tag}")
                chart_points.append(ChartPoint(
                    label=p['name'][:12],
                    value=float(fc.total_forecasted_units),
                    full_label=f"{p['name']}: {fc.total_forecasted_units} units"
                ))

            chart = ChartData(
                kind="bars",
                title=f"Top Forecasted Products ({days} Days)",
                value_label="Projected Units",
                points=chart_points,
                auto_open=True,
            )

            evidence = [
                CopilotEvidenceItem(source_metric="Total Forecast Units", value=f"{total_units} units", context=f"Over next {days} days"),
                CopilotEvidenceItem(source_metric="Projected Revenue", value=f"₹{total_rev:,.0f}", context="Store-wide forward projection"),
                CopilotEvidenceItem(source_metric="Stockout Warnings", value=str(stockout_count), context="Products with insufficient runway"),
            ]

            return CopilotChatResponse(
                reply="\n".join(lines).strip(),
                evidence=evidence,
                draft_action=None,
                chart=chart,
                llm_configured=True,
                provider_info="LocalPulse Agent Tool: get_demand_forecast",
            )
