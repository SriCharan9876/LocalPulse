from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class CampaignCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=120)
    campaign_type: str = Field("Special Discount", description="'Special Discount' or 'Festival Discount'")
    target_product_ids: List[str] = Field(default_factory=list)
    collaboration_proposal_id: Optional[str] = None
    discount_pct: float = Field(10.0, ge=1, le=50)
    budget_allocated: float = Field(1500.0, ge=0)
    start_date: str
    end_date: str
    target_redemptions_goal: int = Field(50, ge=5)

class SimulateRedemptionRequest(BaseModel):
    count: int = Field(1, ge=1, le=50, description="Number of customer redemptions to simulate")

class CampaignPerformanceResponse(BaseModel):
    campaign_id: str
    merchant_id: str
    title: str
    campaign_type: str
    status: str  # "ACTIVE", "PAUSED", "COMPLETED"
    discount_pct: float
    budget_allocated: float
    start_date: str
    end_date: str
    target_redemptions_goal: int
    
    # Real simulated metrics
    total_redemptions: int
    total_revenue_generated: float
    total_discounts_granted: float
    cost_of_goods_sold: float
    net_campaign_profit: float
    return_on_marketing_spend_pct: float
    
    # Baseline comparison
    baseline_expected_revenue: float
    incremental_revenue_lift: float
    lift_pct: float
    
    is_simulated_activity: bool = True
    simulation_disclaimer: str = "Deterministic synthetic campaign simulator for hackathon demonstration. All customer redemptions and margin metrics are derived from realistic localized parameters."
    created_at: datetime
