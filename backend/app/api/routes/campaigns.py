import uuid
from datetime import datetime, date, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.session import get_database
from app.api.dependencies import get_current_merchant
from app.services.campaign import campaign_service
from app.schemas.campaign import (
    CampaignCreate, SimulateRedemptionRequest, CampaignPerformanceResponse
)

router = APIRouter(prefix="/campaigns", tags=["Campaign Results & Simulation"])

@router.get("", response_model=List[CampaignPerformanceResponse])
async def list_campaigns(
    merchant: dict = Depends(get_current_merchant),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    List all promotional campaigns and their real-time calculated performance
    metrics derived from persisted simulated redemption records.
    """
    m_id = merchant["merchant_id"]
    cursor = db.campaigns.find({"merchant_id": m_id}).sort("created_at", -1)
    campaigns = await cursor.to_list(length=50)

    # Calculate baseline average daily revenue from 30d history
    thirty_days_ago = (date.today() - timedelta(days=30)).strftime("%Y-%m-%d")
    sales = await db.sales.find({
        "merchant_id": m_id,
        "date": {"$gte": thirty_days_ago}
    }).to_list(length=500)
    total_rev = sum(float(s.get("revenue", 0.0)) for s in sales)
    baseline_daily_rev = (total_rev / 30.0) if total_rev > 0 else 3500.0

    results = []
    for camp in campaigns:
        redemptions = await db.campaign_redemptions.find(
            {"campaign_id": camp["campaign_id"]}
        ).to_list(length=500)

        perf = campaign_service.calculate_performance(
            campaign=camp,
            redemptions=redemptions,
            baseline_daily_revenue=baseline_daily_rev
        )
        results.append(perf)

    return results

@router.post("", response_model=CampaignPerformanceResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    req: CampaignCreate,
    merchant: dict = Depends(get_current_merchant),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Create a new promotional campaign."""
    m_id = merchant["merchant_id"]
    camp_id = f"camp-{uuid.uuid4().hex[:8]}"
    now = datetime.utcnow()

    camp_doc = {
        "campaign_id": camp_id,
        "merchant_id": m_id,
        "title": req.title,
        "campaign_type": req.campaign_type,
        "target_product_ids": req.target_product_ids,
        "collaboration_proposal_id": req.collaboration_proposal_id,
        "discount_pct": req.discount_pct,
        "budget_allocated": req.budget_allocated,
        "start_date": req.start_date,
        "end_date": req.end_date,
        "target_redemptions_goal": req.target_redemptions_goal,
        "status": "ACTIVE",
        "created_at": now,
        "is_synthetic": True,
    }
    await db.campaigns.insert_one(camp_doc)

    # Automatically apply discounted effective_selling_price to all targeted products
    if req.target_product_ids:
        for pid in req.target_product_ids:
            prod = await db.products.find_one({"merchant_id": m_id, "product_id": pid})
            if prod:
                orig_sp = float(prod.get("selling_price", 0.0))
                discounted_price = round(orig_sp * (1.0 - (req.discount_pct / 100.0)), 2)
                await db.products.update_one(
                    {"merchant_id": m_id, "product_id": pid},
                    {"$set": {
                        "effective_selling_price": discounted_price,
                        "active_campaign_id": camp_id
                    }}
                )

    perf = campaign_service.calculate_performance(
        campaign=camp_doc,
        redemptions=[],
        baseline_daily_revenue=3500.0
    )
    return perf

@router.post("/{campaign_id}/end", response_model=CampaignPerformanceResponse)
async def end_campaign(
    campaign_id: str,
    merchant: dict = Depends(get_current_merchant),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    End an active promotional campaign: marks it COMPLETED and restores
    original regular selling prices on all targeted products.
    """
    m_id = merchant["merchant_id"]
    camp = await db.campaigns.find_one({"merchant_id": m_id, "campaign_id": campaign_id})
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Update campaign status
    await db.campaigns.update_one(
        {"merchant_id": m_id, "campaign_id": campaign_id},
        {"$set": {"status": "COMPLETED"}}
    )
    camp["status"] = "COMPLETED"

    # Restore effective_selling_price = selling_price for targeted products
    if camp.get("target_product_ids"):
        for pid in camp["target_product_ids"]:
            prod = await db.products.find_one({"merchant_id": m_id, "product_id": pid})
            if prod:
                orig_sp = float(prod.get("selling_price", 0.0))
                await db.products.update_one(
                    {"merchant_id": m_id, "product_id": pid},
                    {"$set": {
                        "effective_selling_price": orig_sp,
                        "active_campaign_id": None
                    }}
                )

    # Recalculate and return performance
    all_redemptions = await db.campaign_redemptions.find(
        {"campaign_id": campaign_id}
    ).to_list(length=500)

    perf = campaign_service.calculate_performance(
        campaign=camp,
        redemptions=all_redemptions,
        baseline_daily_revenue=3500.0
    )
    return perf

@router.post("/{campaign_id}/simulate-redemptions", response_model=CampaignPerformanceResponse)
async def simulate_redemptions(
    campaign_id: str,
    req: SimulateRedemptionRequest,
    merchant: dict = Depends(get_current_merchant),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Simulate customer redemptions for a campaign.
    Persists deterministic redemption records, consumes product inventory,
    and returns recalculated campaign metrics.
    """
    m_id = merchant["merchant_id"]
    camp = await db.campaigns.find_one({"merchant_id": m_id, "campaign_id": campaign_id})
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Fetch targeted products
    target_prods = []
    if camp.get("target_product_ids"):
        target_prods = await db.products.find({
            "merchant_id": m_id,
            "product_id": {"$in": camp["target_product_ids"]}
        }).to_list(length=10)

    # Generate redemptions
    new_redemptions = campaign_service.generate_simulated_redemptions(
        campaign_id=campaign_id,
        merchant_id=m_id,
        count=req.count,
        discount_pct=float(camp.get("discount_pct", 10.0)),
        target_products=target_prods
    )
    if new_redemptions:
        await db.campaign_redemptions.insert_many(new_redemptions)

        # Realistically deduct units from inventory for targeted products
        if target_prods:
            units_per_sku = max(1, req.count // len(target_prods))
            for p in target_prods:
                current = int(p.get("current_stock", 0))
                updated_stock = max(0, current - units_per_sku)
                await db.products.update_one(
                    {"merchant_id": m_id, "product_id": p["product_id"]},
                    {"$set": {"current_stock": updated_stock}}
                )

    # Recalculate
    all_redemptions = await db.campaign_redemptions.find(
        {"campaign_id": campaign_id}
    ).to_list(length=500)

    perf = campaign_service.calculate_performance(
        campaign=camp,
        redemptions=all_redemptions,
        baseline_daily_revenue=3500.0
    )
    return perf
