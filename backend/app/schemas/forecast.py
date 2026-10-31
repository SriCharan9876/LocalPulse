from pydantic import BaseModel
from typing import List, Optional

class DailyForecastPoint(BaseModel):
    date: str  # YYYY-MM-DD
    day_name: str
    predicted_units: int
    projected_revenue: float
    is_weekend: bool

class ProductForecastResponse(BaseModel):
    product_id: str
    product_name: str
    category: str
    current_stock: int
    reorder_threshold: int
    selling_price: float
    effective_selling_price: float
    is_promotional: bool = False
    daily_forecasts: List[DailyForecastPoint]
    total_forecasted_units: int
    total_projected_revenue: float
    method_used: str  # e.g., "7-Day & 28-Day Weekday-Weighted Historical Baseline"
    historical_window_days: int
    data_sufficiency_warning: Optional[str] = None
    days_of_inventory_remaining: float
    stockout_risk: bool
    recommended_replenishment_units: int
    explanation: str

class BatchForecastSummary(BaseModel):
    forecast_generated_at: str
    forecast_horizon_days: int = 7
    products_analyzed: int
    total_forecasted_units: int
    total_projected_revenue: float
    high_stockout_risk_count: int
    forecasts: List[ProductForecastResponse]
