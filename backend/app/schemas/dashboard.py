from pydantic import BaseModel
from typing import List, Optional
from app.schemas.sales import DailySaleRecord
from app.schemas.forecast import DailyForecastPoint

class StockWarningItem(BaseModel):
    product_id: str
    product_name: str
    category: str
    current_stock: int
    reorder_threshold: int
    days_of_stock_left: float
    recommended_reorder: int
    severity: str  # "CRITICAL", "WARNING", "HEALTHY"

class GrowthRecommendation(BaseModel):
    recommendation_id: str
    title: str
    category: str  # "INVENTORY_OPTIMIZATION", "CLEARANCE_DISCOUNT", "MIN_MARGIN_DISCOUNT"
    summary: str
    rationale: str
    projected_revenue_lift: float
    confidence_level: str  # "HIGH", "MEDIUM"
    action_type: str  # "CREATE_CAMPAIGN", "RESTOCK_PRODUCT"
    action_payload: dict

class ActionRecommendationItem(BaseModel):
    recommendation_id: str
    category_type: str  # "RESTOCK_PRIORITY", "CLEARANCE_DISCOUNT", "MIN_MARGIN_DISCOUNT"
    badge_label: str    # "Restock Priority", "Excess Clearance", "Min. Margin Discount"
    title: str
    product_id: str
    product_name: str
    current_stock: int
    metric_highlight: str
    summary: str
    rationale: str
    suggested_discount_pct: Optional[float] = None
    recommended_quantity: Optional[int] = None
    projected_revenue_lift: float
    action_type: str  # "RESTOCK_PRODUCT", "CREATE_CAMPAIGN"
    action_url: str   # "/demand" or "/campaigns"

class DashboardSummaryResponse(BaseModel):
    merchant_id: str
    business_name: str
    category: str
    total_revenue_30d: float
    revenue_growth_pct: float
    total_orders_30d: int
    avg_order_value: float
    low_stock_items_count: int
    growth_health_score: int  # 0-100
    sales_history_30d: List[DailySaleRecord]
    seven_day_forecast_summary: List[DailyForecastPoint]
    stock_warnings: List[StockWarningItem]
    prioritized_growth_recommendation: Optional[GrowthRecommendation] = None
    top_recommendations: List[ActionRecommendationItem] = []
