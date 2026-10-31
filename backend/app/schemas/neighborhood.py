from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import date, datetime

class MerchantCoordinates(BaseModel):
    lat: float
    lng: float

class NearbyMerchant(BaseModel):
    merchant_id: str
    business_name: str
    category: str
    address: str
    phone: str
    latitude: float
    longitude: float
    coordinates: MerchantCoordinates
    distance_km: float
    distance_meters: int
    synergy_type: Optional[str] = None
    synergy_score: Optional[int] = None
    top_products: List[dict] = Field(default_factory=list)

class EventCategoryImpact(BaseModel):
    category: str
    multiplier: float
    projected_demand_change_pct: int
    highlight_products: List[str] = Field(default_factory=list)

class NeighborhoodEvent(BaseModel):
    event_id: str
    title: str
    description: str
    start_date: str
    end_date: str
    location_name: Optional[str] = None
    coordinates: Optional[MerchantCoordinates] = None
    distance_km: Optional[float] = None
    category_impacts: List[EventCategoryImpact] = Field(default_factory=list)
    recommended_action: str
    severity: str = "HIGH"  # HIGH, MEDIUM, LOW
    source: Optional[str] = "Calendarific All-India API"

class NeighborhoodSummary(BaseModel):
    current_merchant_id: str
    current_merchant_name: str
    current_merchant_category: str
    current_coordinates: MerchantCoordinates
    nearby_merchants_count: int
    upcoming_events_count: int
    events_source: Optional[str] = "All-India Live Occasions"
    nearest_partner_name: Optional[str] = None
    nearest_partner_distance_km: Optional[float] = None
