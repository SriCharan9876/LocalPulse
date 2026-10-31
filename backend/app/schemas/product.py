from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

class ProductCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    category: str = Field(..., min_length=2, max_length=60)
    cost_price: float = Field(..., gt=0, description="Cost per unit in INR")
    selling_price: float = Field(..., gt=0, description="Retail selling price in INR")
    effective_selling_price: Optional[float] = Field(None, gt=0, description="Active price after discounts")
    current_stock: int = Field(..., ge=0, description="Stock on hand")
    reorder_threshold: int = Field(..., ge=0, description="Threshold for low-stock warning")
    unit: str = Field("units", description="Unit of measure (units, kg, packs, liters)")

class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=120)
    category: Optional[str] = Field(None, min_length=2, max_length=60)
    cost_price: Optional[float] = Field(None, gt=0)
    selling_price: Optional[float] = Field(None, gt=0)
    effective_selling_price: Optional[float] = Field(None, gt=0)
    current_stock: Optional[int] = Field(None, ge=0)
    reorder_threshold: Optional[int] = Field(None, ge=0)
    unit: Optional[str] = None

class ProductResponse(BaseModel):
    product_id: str
    merchant_id: str
    name: str
    category: str
    cost_price: float
    selling_price: float
    effective_selling_price: float
    active_campaign_id: Optional[str] = None
    current_stock: int
    reorder_threshold: int
    unit: str
    created_at: datetime
    updated_at: datetime

class InventoryAdjustmentRequest(BaseModel):
    adjustment_type: Literal["RESTOCK", "DAMAGE_LOSS", "AUDIT_CORRECTION"]
    quantity: int = Field(..., gt=0, description="Positive quantity to adjust")
    notes: Optional[str] = Field(None, max_length=250)

class InventoryMovementResponse(BaseModel):
    movement_id: str
    merchant_id: str
    product_id: str
    product_name: str
    adjustment_type: str
    quantity_change: int
    stock_before: int
    stock_after: int
    notes: Optional[str]
    created_at: datetime
