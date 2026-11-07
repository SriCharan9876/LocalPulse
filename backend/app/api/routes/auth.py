import uuid
import random
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.session import get_database
from app.core.security import verify_password, get_password_hash, create_access_token
from app.schemas.auth import (
    LoginRequest, SignupRequest, Token, MerchantProfile, MerchantProfileUpdate, SwitchDemoMerchantRequest
)
from app.api.dependencies import get_current_merchant

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=Token)
async def login(req: LoginRequest, db: AsyncIOMotorDatabase = Depends(get_database)):
    """Authenticate merchant with email and password."""
    merchant = await db.merchants.find_one({"email": req.email.lower()})
    if not merchant or not verify_password(req.password, merchant.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": merchant["merchant_id"]})
    profile = MerchantProfile(
        merchant_id=merchant["merchant_id"],
        business_name=merchant["business_name"],
        owner_name=merchant["owner_name"],
        email=merchant["email"],
        category=merchant.get("category", "Retail"),
        address=merchant.get("address", ""),
        phone=merchant.get("phone", ""),
        latitude=merchant.get("latitude"),
        longitude=merchant.get("longitude"),
        coordinates=merchant.get("coordinates") or (
            {"lat": merchant.get("latitude"), "lng": merchant.get("longitude")}
            if merchant.get("latitude") is not None and merchant.get("longitude") is not None
            else None
        ),
        created_at=merchant.get("created_at", datetime.utcnow()),
    )
    return Token(access_token=access_token, merchant=profile)

@router.post("/signup", response_model=Token, status_code=status.HTTP_201_CREATED)
async def signup(req: SignupRequest, db: AsyncIOMotorDatabase = Depends(get_database)):
    """Register a new merchant account."""
    existing = await db.merchants.find_one({"email": req.email.lower()})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists"
        )

    merchant_id = f"merchant-{uuid.uuid4().hex[:8]}"
    now = datetime.utcnow()

    # Assign coordinates: use provided or generate realistic Bengaluru neighborhood cluster offset (~100-450m)
    lat = req.latitude
    lng = req.longitude
    if lat is None or lng is None:
        lat = round(12.920737 + random.uniform(-0.0035, 0.0035), 6)
        lng = round(77.668710 + random.uniform(-0.0035, 0.0035), 6)

    coords = {"lat": lat, "lng": lng}

    merchant_doc = {
        "merchant_id": merchant_id,
        "business_name": req.business_name,
        "owner_name": req.owner_name,
        "email": req.email.lower(),
        "password_hash": get_password_hash(req.password),
        "category": req.category,
        "address": req.address,
        "phone": req.phone,
        "latitude": lat,
        "longitude": lng,
        "coordinates": coords,
        "created_at": now,
        "is_synthetic": False,
    }
    await db.merchants.insert_one(merchant_doc)

    access_token = create_access_token(data={"sub": merchant_id})
    profile = MerchantProfile(
        merchant_id=merchant_id,
        business_name=req.business_name,
        owner_name=req.owner_name,
        email=req.email.lower(),
        category=req.category,
        address=req.address,
        phone=req.phone,
        latitude=lat,
        longitude=lng,
        coordinates=coords,
        created_at=now,
    )
    return Token(access_token=access_token, merchant=profile)

@router.get("/me", response_model=MerchantProfile)
async def get_me(merchant: dict = Depends(get_current_merchant)):
    """Retrieve profile for the authenticated merchant."""
    lat = merchant.get("latitude")
    lng = merchant.get("longitude")
    coords = merchant.get("coordinates") or (
        {"lat": lat, "lng": lng} if lat is not None and lng is not None else None
    )
    return MerchantProfile(
        merchant_id=merchant["merchant_id"],
        business_name=merchant["business_name"],
        owner_name=merchant["owner_name"],
        email=merchant["email"],
        category=merchant.get("category", "Retail"),
        address=merchant.get("address", ""),
        phone=merchant.get("phone", ""),
        latitude=lat,
        longitude=lng,
        coordinates=coords,
        created_at=merchant.get("created_at", datetime.utcnow()),
    )

@router.put("/me", response_model=MerchantProfile)
async def update_me(
    req: MerchantProfileUpdate,
    merchant: dict = Depends(get_current_merchant),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Update profile details and storefront map coordinates."""
    m_id = merchant["merchant_id"]
    update_data = {}
    if req.business_name is not None:
        update_data["business_name"] = req.business_name
    if req.owner_name is not None:
        update_data["owner_name"] = req.owner_name
    if req.category is not None:
        update_data["category"] = req.category
    if req.address is not None:
        update_data["address"] = req.address
    if req.phone is not None:
        update_data["phone"] = req.phone
    if req.latitude is not None and req.longitude is not None:
        update_data["latitude"] = req.latitude
        update_data["longitude"] = req.longitude
        update_data["coordinates"] = {"lat": req.latitude, "lng": req.longitude}

    if update_data:
        update_data["updated_at"] = datetime.utcnow()
        await db.merchants.update_one({"merchant_id": m_id}, {"$set": update_data})

    updated = await db.merchants.find_one({"merchant_id": m_id})
    lat = updated.get("latitude")
    lng = updated.get("longitude")
    coords = updated.get("coordinates") or (
        {"lat": lat, "lng": lng} if lat is not None and lng is not None else None
    )
    return MerchantProfile(
        merchant_id=updated["merchant_id"],
        business_name=updated["business_name"],
        owner_name=updated["owner_name"],
        email=updated["email"],
        category=updated.get("category", "Retail"),
        address=updated.get("address", ""),
        phone=updated.get("phone", ""),
        latitude=lat,
        longitude=lng,
        coordinates=coords,
        created_at=updated.get("created_at", datetime.utcnow()),
    )

@router.get("/demo-merchants")
async def list_demo_merchants(db: AsyncIOMotorDatabase = Depends(get_database)):
    """
    List seeded fictional demo merchants for live evaluation.
    Clearly identifies synthetic status.
    """
    cursor = db.merchants.find({"is_synthetic": True}, {"password_hash": 0, "_id": 0})
    merchants = await cursor.to_list(length=20)
    return {
        "demo_notice": "Fictional merchant accounts seeded for hackathon demonstration.",
        "merchants": merchants
    }

@router.post("/switch-demo", response_model=Token)
async def switch_demo_merchant(
    req: SwitchDemoMerchantRequest,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Switch authenticated context to another seeded fictional demo merchant.
    Issues a fully verified JWT so all downstream routes authenticate strictly through backend tokens.
    """
    merchant = await db.merchants.find_one({"merchant_id": req.merchant_id, "is_synthetic": True})
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fictional demo merchant not found"
        )

    access_token = create_access_token(data={"sub": merchant["merchant_id"]})
    lat = merchant.get("latitude")
    lng = merchant.get("longitude")
    coords = merchant.get("coordinates") or (
        {"lat": lat, "lng": lng} if lat is not None and lng is not None else None
    )
    profile = MerchantProfile(
        merchant_id=merchant["merchant_id"],
        business_name=merchant["business_name"],
        owner_name=merchant["owner_name"],
        email=merchant["email"],
        category=merchant.get("category", "Retail"),
        address=merchant.get("address", ""),
        phone=merchant.get("phone", ""),
        latitude=lat,
        longitude=lng,
        coordinates=coords,
        created_at=merchant.get("created_at", datetime.utcnow()),
    )
    return Token(access_token=access_token, merchant=profile)
