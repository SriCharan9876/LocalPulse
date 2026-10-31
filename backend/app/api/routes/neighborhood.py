from datetime import date, timedelta
import math
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.session import get_database
from app.api.dependencies import get_current_merchant
from app.schemas.neighborhood import (
    NearbyMerchant, NeighborhoodEvent, NeighborhoodSummary,
    MerchantCoordinates, EventCategoryImpact,
    EventActionPlanRequest, EventActionPlanResponse,
)
from app.services.collaboration import CATEGORY_SYNERGIES
from app.services.occasions import get_all_india_occasions
from app.services.collab_intelligence import load_suggestions
from app.services.event_actions import build_event_action_plan

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

    # Same partner intelligence as the Collaborations page, so scores and advice match.
    # (Gemini wording is reused from its cache when available; the map never waits on it.)
    suggestions = {s["merchant"]["merchant_id"]: s for s in await load_suggestions(db, merchant, use_ai="cache")}

    result = []
    for m in all_merchants:
        m_id = m["merchant_id"]
        m_lat = float(m.get("latitude", 12.920737))
        m_lng = float(m.get("longitude", 77.668710))
        dist_km = calculate_haversine(curr_lat, curr_lng, m_lat, m_lng)
        dist_m = int(dist_km * 1000)

        partner_cat = m.get("category", "")
        sug = suggestions.get(m_id)
        bundle = sug["bundle"] if sug else None

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
                synergy_type=sug["theme"] if sug else None,
                synergy_score=sug["score"] if sug else None,
                synergy_rationale=(bundle.get("pitch") if bundle else (sug["rationale"] if sug else None)),
                has_bundle=bool(bundle),
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
    Retrieve real All-India occasions, religious festivals, and neighborhood events
    with calculated proximity and category demand impacts for the merchant's store.
    """
    curr_lat = float(merchant.get("latitude", 12.920737))
    curr_lng = float(merchant.get("longitude", 77.668710))
    curr_cat = merchant.get("category", "")

    events, _ = await get_all_india_occasions(
        merchant=merchant,
        merchant_lat=curr_lat,
        merchant_lng=curr_lng,
        merchant_category=curr_cat,
        db=db
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
    curr_cat = merchant.get("category", "")

    all_merchants = await db.merchants.find({"merchant_id": {"$ne": current_m_id}}).to_list(length=50)
    events, source_name = await get_all_india_occasions(
        merchant=None,
        merchant_lat=curr_lat,
        merchant_lng=curr_lng,
        merchant_category=curr_cat,
        db=db
    )
    events_count = len(events)

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
        events_source=source_name,
        nearest_partner_name=nearest_partner,
        nearest_partner_distance_km=min_dist if nearest_partner else None,
    )


@router.post("/events/action-plan", response_model=EventActionPlanResponse)
async def get_event_action_plan(
    req: EventActionPlanRequest,
    merchant: dict = Depends(get_current_merchant),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Concrete actions for one occasion (restock drafts, a small festival offer, partner
    bundle ideas). Read-only: each draft is applied only when the merchant confirms it
    (via /copilot/confirm-action, which re-checks every safety rule).
    """
    m_id = merchant["merchant_id"]
    products = await db.products.find({"merchant_id": m_id}).to_list(length=200)
    since = (date.today() - timedelta(days=120)).isoformat()
    sales = await db.sales.find({"merchant_id": m_id, "date": {"$gte": since}}).to_list(length=None)
    try:
        partners = await load_suggestions(db, merchant, use_ai="cache")
    except Exception:
        partners = []
    next_occurrence = None
    has_passed = (req.end_date or req.start_date) < date.today().isoformat()
    if has_passed:
        next_occurrence = await _find_next_occurrence(req.title, merchant)
    plan = build_event_action_plan(req.model_dump(), merchant, products, sales, partners,
                                   next_occurrence=next_occurrence)
    return EventActionPlanResponse(**plan)


async def _find_next_occurrence(title: str, merchant: dict):
    """The next upcoming date of the same occasion in the calendar feed (None if not listed).
    The feed is cached; a slow or unreachable calendar is skipped after 3 seconds."""
    import asyncio
    import re as _re

    def norm(t: str) -> str:
        return _re.sub(r"[^a-z]", "", (t or "").lower())

    try:
        events, _ = await asyncio.wait_for(
            get_all_india_occasions(
                merchant=None,
                merchant_lat=float(merchant.get("latitude", 12.920737)),
                merchant_lng=float(merchant.get("longitude", 77.668710)),
                merchant_category=merchant.get("category", ""),
                db=None,
            ),
            timeout=3.0,
        )
    except Exception:
        return None
    today = date.today().isoformat()
    key = norm(title)
    upcoming = [e for e in events if norm(e.title) == key and e.start_date > today]
    if not upcoming:
        return None
    return min(upcoming, key=lambda e: e.start_date).model_dump()
