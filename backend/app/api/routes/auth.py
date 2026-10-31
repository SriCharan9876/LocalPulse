import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.session import get_database
from app.core.security import verify_password, get_password_hash, create_access_token
from app.schemas.auth import (
    LoginRequest, SignupRequest, Token, MerchantProfile, SwitchDemoMerchantRequest
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
    merchant_doc = {
        "merchant_id": merchant_id,
        "business_name": req.business_name,
        "owner_name": req.owner_name,
        "email": req.email.lower(),
        "password_hash": get_password_hash(req.password),
        "category": req.category,
        "address": req.address,
        "phone": req.phone,
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
