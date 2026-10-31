import random
from datetime import datetime, date
from typing import List, Dict, Optional
from app.schemas.campaign import CampaignPerformanceResponse

class CampaignService:
    def calculate_performance(
        self,
        campaign: dict,
        redemptions: List[dict],
        baseline_daily_revenue: float
    ) -> CampaignPerformanceResponse:
        """
        Calculate deterministic financial performance metrics from persisted
        simulated redemption records and compare against defined non-promoted baseline.
        """
        c_id = campaign["campaign_id"]
        m_id = campaign["merchant_id"]
        title = campaign["title"]
        c_type = campaign.get("campaign_type", "DISCOUNT_OFFER")
        status = campaign.get("status", "ACTIVE")
        budget = float(campaign.get("budget_allocated", 1500.0))
        discount_pct = float(campaign.get("discount_pct", 10.0))
        goal = int(campaign.get("target_redemptions_goal", 50))
        start_date = campaign.get("start_date", "")
        end_date = campaign.get("end_date", "")

        total_redemptions = len(redemptions)
        total_revenue = sum(float(r.get("order_value", 0.0)) for r in redemptions)
        total_discounts = sum(float(r.get("discount_amount", 0.0)) for r in redemptions)
        total_cogs = sum(float(r.get("estimated_cogs", 0.0)) for r in redemptions)

        # Net campaign profit = Generated Revenue - COGS - Budget Allocated
        net_profit = round(total_revenue - total_cogs - budget, 2)
        
        # Return on Marketing Spend (ROAS / ROMS %)
        roms_pct = round(((total_revenue - budget) / budget * 100.0), 2) if budget > 0 else 0.0

        # Baseline comparison
        # Baseline revenue expected over campaign duration without promotional stimulus
        # Assume campaign length or elapsed days
        try:
            d_start = date.fromisoformat(start_date)
            d_end = date.fromisoformat(end_date)
            duration_days = max(1, (d_end - d_start).days + 1)
        except Exception:
            duration_days = 7

        baseline_expected = round(baseline_daily_revenue * duration_days * 0.45, 2)  # target category fraction
        incremental_lift = round(total_revenue - baseline_expected, 2)
        lift_pct = round((incremental_lift / baseline_expected * 100.0), 2) if baseline_expected > 0 else 0.0

        return CampaignPerformanceResponse(
            campaign_id=c_id,
            merchant_id=m_id,
            title=title,
            campaign_type=c_type,
            status=status,
            discount_pct=discount_pct,
            budget_allocated=budget,
            start_date=start_date,
            end_date=end_date,
            target_redemptions_goal=goal,
            total_redemptions=total_redemptions,
            total_revenue_generated=round(total_revenue, 2),
            total_discounts_granted=round(total_discounts, 2),
            cost_of_goods_sold=round(total_cogs, 2),
            net_campaign_profit=net_profit,
            return_on_marketing_spend_pct=roms_pct,
            baseline_expected_revenue=baseline_expected,
            incremental_revenue_lift=incremental_lift,
            lift_pct=lift_pct,
            is_simulated_activity=True,
            created_at=campaign.get("created_at", datetime.utcnow()),
        )

    def generate_simulated_redemptions(
        self,
        campaign_id: str,
        merchant_id: str,
        count: int,
        discount_pct: float,
        target_products: List[dict]
    ) -> List[dict]:
        """
        Generate deterministic simulated customer redemptions for demonstration purposes.
        """
        rng = random.Random()
        new_redemptions = []
        now = datetime.utcnow()

        avg_regular = (
            sum(float(p.get("selling_price", 320.0)) for p in target_products) / len(target_products)
            if target_products else 320.0
        )
        avg_effective = (
            sum(float(p.get("effective_selling_price", p.get("selling_price", 320.0))) for p in target_products) / len(target_products)
            if target_products else round(320.0 * (1.0 - discount_pct / 100.0), 2)
        )
        avg_cost = (
            sum(float(p.get("cost_price", 240.0)) for p in target_products) / len(target_products)
            if target_products else 240.0
        )

        for i in range(count):
            mult = rng.uniform(0.9, 1.4)
            order_val = round(avg_effective * mult, 2)
            disc_amt = round((avg_regular - avg_effective) * mult, 2)
            cogs = round(avg_cost * mult, 2)

            new_redemptions.append({
                "redemption_id": f"red-{campaign_id}-{int(now.timestamp())}-{i+1}",
                "campaign_id": campaign_id,
                "merchant_id": merchant_id,
                "redeemed_at": now,
                "order_value": order_val,
                "discount_amount": disc_amt,
                "estimated_cogs": cogs,
                "is_simulated": True,
            })

        return new_redemptions

campaign_service = CampaignService()
