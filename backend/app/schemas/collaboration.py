from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class ComplementaryProductInfo(BaseModel):
    product_id: str
    name: str
    category: str
    selling_price: float
    cost_price: float

class SuggestedBundle(BaseModel):
    """Best bundle with this partner: products, cost-safe discounts and the reasons."""
    bundle_name: str
    pitch: str
    theme: str
    initiator_product_id: str
    initiator_product_name: str
    initiator_discount_pct: float
    initiator_margin_pct: float
    partner_product_id: str
    partner_product_name: str
    partner_discount_pct: float
    partner_margin_pct: float
    original_bundle_price: float
    discounted_bundle_price: float
    effective_bundle_discount_pct: float
    festival: Optional[str] = None

class DiscoverablePartner(BaseModel):
    merchant_id: str
    business_name: str
    category: str
    address: str
    distance_km: float
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    coordinates: Optional[dict] = None
    synergy_type: str  # e.g., "Morning Breakfast Combo", "Sweet & Savory", "Daily Staples"
    synergy_rationale: str
    complementary_score: int  # 1-100
    top_products: List[ComplementaryProductInfo]
    suggested_bundle: Optional[SuggestedBundle] = None
    suggestion_reasons: List[str] = Field(default_factory=list)
    suggestion_source: Optional[str] = None  # "Gemini-assisted" or "LocalPulse rules"

class MarginValidationRequest(BaseModel):
    initiator_product_id: str
    initiator_discount_pct: float = Field(..., ge=0, le=50)
    partner_merchant_id: str
    partner_product_id: str
    partner_discount_pct: float = Field(..., ge=0, le=50)
    # Optional: the Collaborations page checks margins live before a name is final
    bundle_name: str = "Joint Bundle"

class MarginValidationResponse(BaseModel):
    bundle_name: str
    original_bundle_price: float
    discounted_bundle_price: float
    effective_bundle_discount_pct: float
    
    initiator_product_name: str
    initiator_original_price: float
    initiator_discounted_price: float
    initiator_cost: float
    initiator_margin_pct: float
    initiator_profit_per_unit: float
    
    partner_product_name: str
    partner_original_price: float
    partner_discounted_price: float
    partner_cost: float
    partner_margin_pct: float
    partner_profit_per_unit: float
    
    min_required_margin_pct: float = 12.0
    is_financially_viable: bool
    status_reason: str

class CollaborationProposalCreate(BaseModel):
    partner_merchant_id: str
    initiator_product_id: str
    initiator_discount_pct: float = Field(..., ge=0, le=50)
    partner_product_id: str
    partner_discount_pct: float = Field(..., ge=0, le=50)
    bundle_name: str = Field(..., min_length=3, max_length=120)
    bundle_description: str = Field(..., min_length=5, max_length=300)
    proposed_duration_days: int = Field(14, ge=3, le=60)

class CollaborationProposalResponse(BaseModel):
    proposal_id: str
    bundle_name: str
    bundle_description: str
    initiator_merchant_id: str
    initiator_merchant_name: str
    initiator_product_id: str
    initiator_product_name: str
    initiator_discount_pct: float
    initiator_margin_pct: float
    initiator_approved: bool

    partner_merchant_id: str
    partner_merchant_name: str
    partner_product_id: str
    partner_product_name: str
    partner_discount_pct: float
    partner_margin_pct: float
    partner_approved: bool

    original_bundle_price: float
    discounted_bundle_price: float
    status: str  # "PENDING_APPROVAL", "APPROVED", "REJECTED", "ACTIVE"
    created_at: datetime
    updated_at: datetime
