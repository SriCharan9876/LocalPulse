import uuid
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.session import get_database
from app.api.dependencies import get_current_merchant
from app.services.collaboration import collaboration_service
from app.services.collab_intelligence import load_suggestions
from app.schemas.collaboration import (
    DiscoverablePartner, MarginValidationRequest, MarginValidationResponse,
    CollaborationProposalCreate, CollaborationProposalResponse,
    ComplementaryProductInfo, SuggestedBundle,
)

router = APIRouter(prefix="/collaborations", tags=["Merchant Collaborations"])

@router.get("/discover", response_model=List[DiscoverablePartner])
async def discover_nearby_partners(
    merchant: dict = Depends(get_current_merchant),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Nearby partners ranked by how well a joint bundle would actually work: customer
    buy-together link, my surplus stock, the partner's sales pull, price balance, upcoming
    festivals and distance. Each partner comes with its best cost-safe bundle and the reasons.
    With an LLM key, Gemini picks among the validated bundles and writes the wording.
    """
    suggestions = await load_suggestions(db, merchant, use_ai="yes")

    partners = []
    for s in suggestions:
        m = s["merchant"]
        lat, lng = m.get("latitude"), m.get("longitude")
        partners.append(
            DiscoverablePartner(
                merchant_id=m["merchant_id"],
                business_name=m["business_name"],
                category=m.get("category", ""),
                address=m.get("address", ""),
                distance_km=round(float(s["distance_km"]), 2),
                latitude=lat,
                longitude=lng,
                coordinates=m.get("coordinates") or ({"lat": lat, "lng": lng} if lat is not None and lng is not None else None),
                synergy_type=s["theme"],
                synergy_rationale=s["rationale"],
                complementary_score=s["score"],
                top_products=[
                    ComplementaryProductInfo(
                        product_id=p["product_id"],
                        name=p["name"],
                        category=p.get("category", ""),
                        selling_price=float(p.get("selling_price") or 0),
                        cost_price=float(p.get("cost_price") or 0),
                    )
                    for p in s["ranked_products"][:4]
                ],
                suggested_bundle=SuggestedBundle(**s["bundle"]) if s["bundle"] else None,
                suggestion_reasons=s["reasons"],
                suggestion_source=s["source"] if s["bundle"] else None,
            )
        )
    return partners

@router.post("/validate-margins", response_model=MarginValidationResponse)
async def validate_bundle_margins(
    req: MarginValidationRequest,
    merchant: dict = Depends(get_current_merchant),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Deterministic margin and bundle pricing arithmetic.
    Enforces minimum 12% margin threshold for each participant merchant.
    """
    m_id = merchant["merchant_id"]
    init_prod = await db.products.find_one({"merchant_id": m_id, "product_id": req.initiator_product_id})
    if not init_prod:
        raise HTTPException(status_code=404, detail="Initiator product not found in your catalog")

    partner_prod = await db.products.find_one({"merchant_id": req.partner_merchant_id, "product_id": req.partner_product_id})
    if not partner_prod:
        raise HTTPException(status_code=404, detail="Partner product not found in partner catalog")

    return collaboration_service.validate_bundle_margins(
        initiator_product=init_prod,
        initiator_discount_pct=req.initiator_discount_pct,
        partner_product=partner_prod,
        partner_discount_pct=req.partner_discount_pct,
        bundle_name=req.bundle_name
    )

@router.get("/proposals", response_model=List[CollaborationProposalResponse])
async def list_collaboration_proposals(
    merchant: dict = Depends(get_current_merchant),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    List all collaboration proposals where current merchant is either initiator or partner.
    """
    m_id = merchant["merchant_id"]
    cursor = db.collaborations.find({
        "$or": [
            {"initiator_merchant_id": m_id},
            {"partner_merchant_id": m_id}
        ]
    }).sort("updated_at", -1)

    proposals = await cursor.to_list(length=100)
    return [CollaborationProposalResponse(**p) for p in proposals]

@router.post("/proposals", response_model=CollaborationProposalResponse, status_code=status.HTTP_201_CREATED)
async def create_collaboration_proposal(
    req: CollaborationProposalCreate,
    merchant: dict = Depends(get_current_merchant),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Draft and submit a new collaborative bundle proposal to a partner merchant.
    Validates minimum margins before permitting submission.
    """
    m_id = merchant["merchant_id"]
    if m_id == req.partner_merchant_id:
        raise HTTPException(status_code=400, detail="Cannot create collaboration with yourself")

    init_prod = await db.products.find_one({"merchant_id": m_id, "product_id": req.initiator_product_id})
    if not init_prod:
        raise HTTPException(status_code=404, detail="Initiator product not found")

    partner = await db.merchants.find_one({"merchant_id": req.partner_merchant_id})
    if not partner:
        raise HTTPException(status_code=404, detail="Partner merchant not found")

    partner_prod = await db.products.find_one({"merchant_id": req.partner_merchant_id, "product_id": req.partner_product_id})
    if not partner_prod:
        raise HTTPException(status_code=404, detail="Partner product not found")

    # Run deterministic validation
    val = collaboration_service.validate_bundle_margins(
        initiator_product=init_prod,
        initiator_discount_pct=req.initiator_discount_pct,
        partner_product=partner_prod,
        partner_discount_pct=req.partner_discount_pct,
        bundle_name=req.bundle_name
    )
    if not val.is_financially_viable:
        raise HTTPException(
            status_code=400,
            detail=f"Proposal violates margin safety constraints: {val.status_reason}"
        )

    now = datetime.utcnow()
    prop_id = f"collab-prop-{uuid.uuid4().hex[:8]}"

    prop_doc = {
        "proposal_id": prop_id,
        "bundle_name": req.bundle_name,
        "bundle_description": req.bundle_description,
        "initiator_merchant_id": m_id,
        "initiator_merchant_name": merchant["business_name"],
        "initiator_product_id": init_prod["product_id"],
        "initiator_product_name": init_prod["name"],
        "initiator_discount_pct": req.initiator_discount_pct,
        "initiator_margin_pct": val.initiator_margin_pct,
        "initiator_approved": True,

        "partner_merchant_id": partner["merchant_id"],
        "partner_merchant_name": partner["business_name"],
        "partner_product_id": partner_prod["product_id"],
        "partner_product_name": partner_prod["name"],
        "partner_discount_pct": req.partner_discount_pct,
        "partner_margin_pct": val.partner_margin_pct,
        "partner_approved": False,  # Pending partner merchant approval

        "original_bundle_price": val.original_bundle_price,
        "discounted_bundle_price": val.discounted_bundle_price,
        "status": "PENDING_APPROVAL",
        "proposed_duration_days": req.proposed_duration_days,
        "created_at": now,
        "updated_at": now,
        "is_synthetic": True,
    }

    await db.collaborations.insert_one(prop_doc)
    return CollaborationProposalResponse(**prop_doc)

@router.post("/proposals/{proposal_id}/respond", response_model=CollaborationProposalResponse)
async def respond_to_proposal(
    proposal_id: str,
    action: str,  # "APPROVE" or "REJECT"
    merchant: dict = Depends(get_current_merchant),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Approve or reject a collaboration proposal.
    Strictly enforces that ONLY the designated partner (or initiator) can record approval.
    """
    m_id = merchant["merchant_id"]
    prop = await db.collaborations.find_one({"proposal_id": proposal_id})
    if not prop:
        raise HTTPException(status_code=404, detail="Proposal not found")

    is_partner = (prop["partner_merchant_id"] == m_id)
    is_initiator = (prop["initiator_merchant_id"] == m_id)

    if not is_partner and not is_initiator:
        raise HTTPException(status_code=403, detail="Not authorized to respond to this proposal")

    now = datetime.utcnow()
    if action == "APPROVE":
        if is_partner:
            prop["partner_approved"] = True
        if is_initiator:
            prop["initiator_approved"] = True

        new_status = "APPROVED" if (prop["initiator_approved"] and prop["partner_approved"]) else "PENDING_APPROVAL"
        await db.collaborations.update_one(
            {"proposal_id": proposal_id},
            {
                "$set": {
                    "partner_approved": prop["partner_approved"],
                    "initiator_approved": prop["initiator_approved"],
                    "status": new_status,
                    "updated_at": now,
                }
            }
        )
    elif action == "REJECT":
        await db.collaborations.update_one(
            {"proposal_id": proposal_id},
            {"$set": {"status": "REJECTED", "updated_at": now}}
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use APPROVE or REJECT.")

    updated = await db.collaborations.find_one({"proposal_id": proposal_id})
    return CollaborationProposalResponse(**updated)
