from pydantic import BaseModel
from typing import List, Optional
from datetime import date

class DailySaleRecord(BaseModel):
    date: str  # YYYY-MM-DD
    units_sold: int
    revenue: float
    cogs: float
    gross_profit: float

class ProductSalesHistoryResponse(BaseModel):
    product_id: str
    product_name: str
    category: str
    current_stock: int
    history: List[DailySaleRecord]
    total_units_sold: int
    total_revenue: float
    avg_daily_units: float

class OverallSalesHistoryResponse(BaseModel):
    daily_aggregates: List[DailySaleRecord]
    total_revenue: float
    total_units: int
    date_range_start: str
    date_range_end: str
