import math
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.session import get_database
from app.api.dependencies import get_current_merchant
from app.schemas.neighborhood import (
    NearbyMerchant, NeighborhoodEvent, NeighborhoodSummary,
    MerchantCoordinates, EventCategoryImpact
)
from app.services.collaboration import CATEGORY_SYNERGIES

router = APIRouter(prefix="/neighborhood", tags=["Neighborhood Map & Events"])

def calculate_haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Returns distance in kilometers using the Haversine formula."""
    R = 6371.0  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)

@router.get("/merchants", response_model=List[NearbyMerchant])
async def get_nearby_merchants(
    merchant: dict = Depends(get_current_merchant),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    List all neighborhood merchants relative to the authenticated merchant's shop coordinates.
    Computes exact real-world distance in km and meters, along with category synergies.
    """
    current_m_id = merchant["merchant_id"]
    curr_lat = float(merchant.get("latitude", 12.920737))
    curr_lng = float(merchant.get("longitude", 77.668710))
    current_cat = merchant.get("category", "")

    all_merchants = await db.merchants.find({"merchant_id": {"$ne": current_m_id}}, {"password_hash": 0}).to_list(length=50)
    all_products = await db.products.find({}).to_list(length=300)

    # Group products by merchant_id
    prods_by_m = {}
    for p in all_products:
        p_mid = p.get("merchant_id")
        prods_by_m.setdefault(p_mid, []).append({
            "product_id": p.get("product_id"),
            "name": p.get("name"),
            "category": p.get("category"),
            "selling_price": float(p.get("selling_price", 0)),
            "current_stock": int(p.get("current_stock", 0)),
        })

    result = []
    for m in all_merchants:
        m_id = m["merchant_id"]
        m_lat = float(m.get("latitude", 12.920737))
        m_lng = float(m.get("longitude", 77.668710))
        dist_km = calculate_haversine(curr_lat, curr_lng, m_lat, m_lng)
        dist_m = int(dist_km * 1000)

        partner_cat = m.get("category", "")
        key1 = (current_cat, partner_cat)
        key2 = (partner_cat, current_cat)
        if key1 in CATEGORY_SYNERGIES:
            meta = CATEGORY_SYNERGIES[key1]
        elif key2 in CATEGORY_SYNERGIES:
            meta = CATEGORY_SYNERGIES[key2]
        else:
            meta = {
                "synergy_type": "Neighborhood Cross-Promotion",
                "complementary_score": 70,
            }

        top_prods = prods_by_m.get(m_id, [])[:4]

        result.append(
            NearbyMerchant(
                merchant_id=m_id,
                business_name=m.get("business_name", "Local Store"),
                category=partner_cat,
                address=m.get("address", "Indiranagar, Bengaluru"),
                phone=m.get("phone", "+91 98450 00000"),
                latitude=m_lat,
                longitude=m_lng,
                coordinates=MerchantCoordinates(lat=m_lat, lng=m_lng),
                distance_km=dist_km,
                distance_meters=dist_m,
                synergy_type=meta.get("synergy_type"),
                synergy_score=meta.get("complementary_score"),
                top_products=top_prods,
            )
        )

    # Sort closest first
    result.sort(key=lambda x: x.distance_km)
    return result

@router.get("/events", response_model=List[NeighborhoodEvent])
async def get_neighborhood_events(
    merchant: dict = Depends(get_current_merchant),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Retrieve upcoming neighborhood calendar events with calculated proximity
    and category demand impacts for the merchant's store.
    """
    curr_lat = float(merchant.get("latitude", 12.920737))
    curr_lng = float(merchant.get("longitude", 77.668710))

    raw_events = await db.neighborhood_events.find({}).sort("start_date", 1).to_list(length=50)

    events = []
    for ev in raw_events:
        coords = ev.get("coordinates", {"lat": 12.9215, "lng": 77.6692})
        ev_lat = float(coords.get("lat", 12.9215))
        ev_lng = float(coords.get("lng", 77.6692))
        dist_km = calculate_haversine(curr_lat, curr_lng, ev_lat, ev_lng)

        impacts = [
            EventCategoryImpact(
                category=imp.get("category", ""),
                multiplier=float(imp.get("multiplier", 1.0)),
                projected_demand_change_pct=int(imp.get("projected_demand_change_pct", 0)),
                highlight_products=imp.get("highlight_products", [])
            )
            for imp in ev.get("category_impacts", [])
        ]

        events.append(
            NeighborhoodEvent(
                event_id=ev.get("event_id", "ev-gen"),
                title=ev.get("title", ""),
                description=ev.get("description", ""),
                start_date=ev.get("start_date", ""),
                end_date=ev.get("end_date", ""),
                location_name=ev.get("location_name", ""),
                coordinates=MerchantCoordinates(lat=ev_lat, lng=ev_lng),
                distance_km=dist_km,
                category_impacts=impacts,
                recommended_action=ev.get("recommended_action", ""),
                severity=ev.get("severity", "MEDIUM")
            )
        )

    return events

@router.get("/summary", response_model=NeighborhoodSummary)
async def get_neighborhood_summary(
    merchant: dict = Depends(get_current_merchant),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    High-level summary of the merchant's spatial footprint and community calendar status.
    """
    current_m_id = merchant["merchant_id"]
    curr_lat = float(merchant.get("latitude", 12.920737))
    curr_lng = float(merchant.get("longitude", 77.668710))

    all_merchants = await db.merchants.find({"merchant_id": {"$ne": current_m_id}}).to_list(length=50)
    events_count = await db.neighborhood_events.count_documents({})

    nearest_partner = None
    min_dist = 9999.0
    for m in all_merchants:
        m_lat = float(m.get("latitude", 12.920737))
        m_lng = float(m.get("longitude", 77.668710))
        d = calculate_haversine(curr_lat, curr_lng, m_lat, m_lng)
        if d < min_dist:
            min_dist = d
            nearest_partner = m.get("business_name")

    return NeighborhoodSummary(
        current_merchant_id=current_m_id,
        current_merchant_name=merchant.get("business_name", ""),
        current_merchant_category=merchant.get("category", ""),
        current_coordinates=MerchantCoordinates(lat=curr_lat, lng=curr_lng),
        nearby_merchants_count=len(all_merchants),
        upcoming_events_count=events_count,
        nearest_partner_name=nearest_partner,
        nearest_partner_distance_km=min_dist if nearest_partner else None,
    )
