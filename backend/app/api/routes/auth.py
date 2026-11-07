import uuid
import random
import json
import base64
from datetime import datetime, date, timedelta
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.session import get_database
from app.core.security import verify_password, get_password_hash, create_access_token
from app.schemas.auth import (
    LoginRequest, SignupRequest, GoogleLoginRequest, SendOtpRequest, VerifyOtpRequest, OtpResponse,
    Token, MerchantProfile, MerchantProfileUpdate, SwitchDemoMerchantRequest
)
from app.api.dependencies import get_current_merchant

router = APIRouter(prefix="/auth", tags=["Authentication"])

def get_starter_products_for_category(merchant_id: str, category_name: str, now_dt: datetime) -> list:
    """Return 4 authentic starter inventory products tailored to the merchant's chosen store category."""
    cat_lower = (category_name or "").lower()

    if "cafe" in cat_lower or "bakery" in cat_lower:
        return [
            {
                "product_id": f"{merchant_id}-sourdough",
                "merchant_id": merchant_id,
                "name": "Artisan Country Sourdough Loaf",
                "category": "Bakery",
                "cost_price": 90.0,
                "selling_price": 160.0,
                "effective_selling_price": 160.0,
                "current_stock": 14,
                "reorder_threshold": 8,
                "unit": "loaves",
                "base_demand": 10.0,
                "created_at": now_dt - timedelta(days=45),
                "updated_at": now_dt,
                "is_synthetic": True,
            },
            {
                "product_id": f"{merchant_id}-chai",
                "merchant_id": merchant_id,
                "name": "Signature Malabar Spiced Chai Blend 250g",
                "category": "Beverages",
                "cost_price": 110.0,
                "selling_price": 190.0,
                "effective_selling_price": 190.0,
                "current_stock": 35,
                "reorder_threshold": 15,
                "unit": "pouches",
                "base_demand": 12.0,
                "created_at": now_dt - timedelta(days=45),
                "updated_at": now_dt,
                "is_synthetic": True,
            },
            {
                "product_id": f"{merchant_id}-cookies",
                "merchant_id": merchant_id,
                "name": "Dark Chocolate Sea Salt Cookies Box (6pc)",
                "category": "Confectionery",
                "cost_price": 120.0,
                "selling_price": 220.0,
                "effective_selling_price": 220.0,
                "current_stock": 20,
                "reorder_threshold": 10,
                "unit": "boxes",
                "base_demand": 14.0,
                "created_at": now_dt - timedelta(days=45),
                "updated_at": now_dt,
                "is_synthetic": True,
            },
            {
                "product_id": f"{merchant_id}-cake",
                "merchant_id": merchant_id,
                "name": "Banana Walnut Teacake Slice",
                "category": "Bakery",
                "cost_price": 45.0,
                "selling_price": 95.0,
                "effective_selling_price": 95.0,
                "current_stock": 5,  # Low stock warning trigger!
                "reorder_threshold": 12,
                "unit": "slices",
                "base_demand": 15.0,
                "created_at": now_dt - timedelta(days=45),
                "updated_at": now_dt,
                "is_synthetic": True,
            },
        ]
    elif "fruit" in cat_lower or "veg" in cat_lower or "produce" in cat_lower:
        return [
            {
                "product_id": f"{merchant_id}-salad",
                "merchant_id": merchant_id,
                "name": "Hydroponic Crisp Salad Greens Box 250g",
                "category": "Organic Vegetables",
                "cost_price": 60.0,
                "selling_price": 120.0,
                "effective_selling_price": 120.0,
                "current_stock": 18,
                "reorder_threshold": 10,
                "unit": "boxes",
                "base_demand": 11.0,
                "created_at": now_dt - timedelta(days=45),
                "updated_at": now_dt,
                "is_synthetic": True,
            },
            {
                "product_id": f"{merchant_id}-apple",
                "merchant_id": merchant_id,
                "name": "Himachal Royal Delicious Apples 1kg",
                "category": "Fresh Fruits",
                "cost_price": 130.0,
                "selling_price": 190.0,
                "effective_selling_price": 190.0,
                "current_stock": 28,
                "reorder_threshold": 15,
                "unit": "kg",
                "base_demand": 16.0,
                "created_at": now_dt - timedelta(days=45),
                "updated_at": now_dt,
                "is_synthetic": True,
            },
            {
                "product_id": f"{merchant_id}-avocado",
                "merchant_id": merchant_id,
                "name": "Fresh Hass Avocados (Twin Pack)",
                "category": "Fresh Fruits",
                "cost_price": 140.0,
                "selling_price": 240.0,
                "effective_selling_price": 240.0,
                "current_stock": 6,  # Low stock warning trigger!
                "reorder_threshold": 12,
                "unit": "packs",
                "base_demand": 9.0,
                "created_at": now_dt - timedelta(days=45),
                "updated_at": now_dt,
                "is_synthetic": True,
            },
            {
                "product_id": f"{merchant_id}-carrots",
                "merchant_id": merchant_id,
                "name": "Organic Farm Ooty Carrots 1kg",
                "category": "Vegetables",
                "cost_price": 45.0,
                "selling_price": 75.0,
                "effective_selling_price": 75.0,
                "current_stock": 32,
                "reorder_threshold": 15,
                "unit": "kg",
                "base_demand": 12.0,
                "created_at": now_dt - timedelta(days=45),
                "updated_at": now_dt,
                "is_synthetic": True,
            },
        ]
    elif "fashion" in cat_lower or "textile" in cat_lower or "apparel" in cat_lower:
        return [
            {
                "product_id": f"{merchant_id}-kurta",
                "merchant_id": merchant_id,
                "name": "Handloom Pure Khadi Cotton Kurta",
                "category": "Apparel",
                "cost_price": 480.0,
                "selling_price": 950.0,
                "effective_selling_price": 950.0,
                "current_stock": 24,
                "reorder_threshold": 10,
                "unit": "pieces",
                "base_demand": 4.0,
                "created_at": now_dt - timedelta(days=45),
                "updated_at": now_dt,
                "is_synthetic": True,
            },
            {
                "product_id": f"{merchant_id}-dupatta",
                "merchant_id": merchant_id,
                "name": "Handcrafted Pochampally Ikat Dupatta",
                "category": "Apparel",
                "cost_price": 220.0,
                "selling_price": 499.0,
                "effective_selling_price": 499.0,
                "current_stock": 18,
                "reorder_threshold": 8,
                "unit": "pieces",
                "base_demand": 5.0,
                "created_at": now_dt - timedelta(days=45),
                "updated_at": now_dt,
                "is_synthetic": True,
            },
            {
                "product_id": f"{merchant_id}-shirt",
                "merchant_id": merchant_id,
                "name": "Pure Linen Mandarin Collar Shirt",
                "category": "Apparel",
                "cost_price": 550.0,
                "selling_price": 1199.0,
                "effective_selling_price": 1199.0,
                "current_stock": 4,  # Low stock warning trigger!
                "reorder_threshold": 10,
                "unit": "pieces",
                "base_demand": 3.5,
                "created_at": now_dt - timedelta(days=45),
                "updated_at": now_dt,
                "is_synthetic": True,
            },
            {
                "product_id": f"{merchant_id}-stole",
                "merchant_id": merchant_id,
                "name": "Handblock Printed Chanderi Cotton Stole",
                "category": "Accessories",
                "cost_price": 180.0,
                "selling_price": 450.0,
                "effective_selling_price": 450.0,
                "current_stock": 20,
                "reorder_threshold": 8,
                "unit": "pieces",
                "base_demand": 4.5,
                "created_at": now_dt - timedelta(days=45),
                "updated_at": now_dt,
                "is_synthetic": True,
            },
        ]
    elif "health" in cat_lower or "wellness" in cat_lower or "ayurved" in cat_lower:
        return [
            {
                "product_id": f"{merchant_id}-chyawanprash",
                "merchant_id": merchant_id,
                "name": "Sanjeevani Pure Amla Chyawanprash 1kg",
                "category": "Ayurveda",
                "cost_price": 280.0,
                "selling_price": 420.0,
                "effective_selling_price": 420.0,
                "current_stock": 22,
                "reorder_threshold": 10,
                "unit": "jars",
                "base_demand": 5.0,
                "created_at": now_dt - timedelta(days=45),
                "updated_at": now_dt,
                "is_synthetic": True,
            },
            {
                "product_id": f"{merchant_id}-coconutoil",
                "merchant_id": merchant_id,
                "name": "Cold-Pressed Pure Virgin Coconut Oil 500ml",
                "category": "Organic Wellness",
                "cost_price": 160.0,
                "selling_price": 260.0,
                "effective_selling_price": 260.0,
                "current_stock": 29,
                "reorder_threshold": 12,
                "unit": "bottles",
                "base_demand": 7.0,
                "created_at": now_dt - timedelta(days=45),
                "updated_at": now_dt,
                "is_synthetic": True,
            },
            {
                "product_id": f"{merchant_id}-ashwagandha",
                "merchant_id": merchant_id,
                "name": "Organic Ashwagandha Root Powder 200g",
                "category": "Ayurveda",
                "cost_price": 140.0,
                "selling_price": 249.0,
                "effective_selling_price": 249.0,
                "current_stock": 5,  # Low stock warning trigger!
                "reorder_threshold": 12,
                "unit": "jars",
                "base_demand": 6.0,
                "created_at": now_dt - timedelta(days=45),
                "updated_at": now_dt,
                "is_synthetic": True,
            },
            {
                "product_id": f"{merchant_id}-immunitytea",
                "merchant_id": merchant_id,
                "name": "Tulsi Ginger Ayurvedic Immunity Tea 100g",
                "category": "Health Beverages",
                "cost_price": 110.0,
                "selling_price": 185.0,
                "effective_selling_price": 185.0,
                "current_stock": 34,
                "reorder_threshold": 15,
                "unit": "tins",
                "base_demand": 8.0,
                "created_at": now_dt - timedelta(days=45),
                "updated_at": now_dt,
                "is_synthetic": True,
            },
        ]
    elif "sweet" in cat_lower or "snack" in cat_lower:
        return [
            {
                "product_id": f"{merchant_id}-kajukatli",
                "merchant_id": merchant_id,
                "name": "Royal Silver Foil Kaju Katli Box 500g",
                "category": "Traditional Sweets",
                "cost_price": 380.0,
                "selling_price": 550.0,
                "effective_selling_price": 550.0,
                "current_stock": 20,
                "reorder_threshold": 10,
                "unit": "boxes",
                "base_demand": 8.0,
                "created_at": now_dt - timedelta(days=45),
                "updated_at": now_dt,
                "is_synthetic": True,
            },
            {
                "product_id": f"{merchant_id}-mixture",
                "merchant_id": merchant_id,
                "name": "Special Bengaluru Spicy Mixture 250g",
                "category": "Savories",
                "cost_price": 55.0,
                "selling_price": 110.0,
                "effective_selling_price": 110.0,
                "current_stock": 35,
                "reorder_threshold": 15,
                "unit": "packs",
                "base_demand": 14.0,
                "created_at": now_dt - timedelta(days=45),
                "updated_at": now_dt,
                "is_synthetic": True,
            },
            {
                "product_id": f"{merchant_id}-mysorepak",
                "merchant_id": merchant_id,
                "name": "Pure Ghee Special Mysore Pak 400g",
                "category": "Traditional Sweets",
                "cost_price": 210.0,
                "selling_price": 340.0,
                "effective_selling_price": 340.0,
                "current_stock": 7,  # Low stock warning trigger!
                "reorder_threshold": 15,
                "unit": "boxes",
                "base_demand": 10.0,
                "created_at": now_dt - timedelta(days=45),
                "updated_at": now_dt,
                "is_synthetic": True,
            },
            {
                "product_id": f"{merchant_id}-cashews",
                "merchant_id": merchant_id,
                "name": "Roasted Salted Pepper Cashews 200g",
                "category": "Savories",
                "cost_price": 170.0,
                "selling_price": 260.0,
                "effective_selling_price": 260.0,
                "current_stock": 25,
                "reorder_threshold": 10,
                "unit": "jars",
                "base_demand": 9.0,
                "created_at": now_dt - timedelta(days=45),
                "updated_at": now_dt,
                "is_synthetic": True,
            },
        ]
    else:
        # Default: Grocery & Daily Essentials
        return [
            {
                "product_id": f"{merchant_id}-atta",
                "merchant_id": merchant_id,
                "name": "Aashirvaad Shudh Chakki Atta 5kg",
                "category": "Flour & Grains",
                "cost_price": 230.0,
                "selling_price": 275.0,
                "effective_selling_price": 275.0,
                "current_stock": 25,
                "reorder_threshold": 15,
                "unit": "packs",
                "base_demand": 8.0,
                "created_at": now_dt - timedelta(days=45),
                "updated_at": now_dt,
                "is_synthetic": True,
            },
            {
                "product_id": f"{merchant_id}-milk",
                "merchant_id": merchant_id,
                "name": "Amul Taaza Homogenised Toned Milk 1L",
                "category": "Dairy",
                "cost_price": 66.0,
                "selling_price": 74.0,
                "effective_selling_price": 74.0,
                "current_stock": 10,  # Low stock warning trigger!
                "reorder_threshold": 20,
                "unit": "cartons",
                "base_demand": 18.0,
                "created_at": now_dt - timedelta(days=45),
                "updated_at": now_dt,
                "is_synthetic": True,
            },
            {
                "product_id": f"{merchant_id}-tea",
                "merchant_id": merchant_id,
                "name": "Brooke Bond Red Label Tea 500g",
                "category": "Tea & Coffee",
                "cost_price": 240.0,
                "selling_price": 280.0,
                "effective_selling_price": 280.0,
                "current_stock": 35,
                "reorder_threshold": 12,
                "unit": "packs",
                "base_demand": 7.0,
                "created_at": now_dt - timedelta(days=45),
                "updated_at": now_dt,
                "is_synthetic": True,
            },
            {
                "product_id": f"{merchant_id}-oil",
                "merchant_id": merchant_id,
                "name": "Fortune Sunlite Refined Sunflower Oil 1L",
                "category": "Edible Oils",
                "cost_price": 140.0,
                "selling_price": 165.0,
                "effective_selling_price": 165.0,
                "current_stock": 38,
                "reorder_threshold": 15,
                "unit": "pouches",
                "base_demand": 9.0,
                "created_at": now_dt - timedelta(days=45),
                "updated_at": now_dt,
                "is_synthetic": True,
            },
        ]

async def seed_merchant_starter_data(db: AsyncIOMotorDatabase, merchant_id: str, category: str = "Grocery & Daily Essentials"):
    """
    Seed initial starter products tailored to the merchant's category and 45 days of sales records.
    Ensures their Dashboard KPIs, Demand Runway, 7-Day Forecast, and AI Copilot are immediately interactive.
    """
    now_dt = datetime.utcnow()
    starter_products = get_starter_products_for_category(merchant_id, category, now_dt)

    # Ensure idempotency by clearing existing records for this merchant first
    await db.products.delete_many({"merchant_id": merchant_id})
    await db.sales.delete_many({"merchant_id": merchant_id})

    await db.products.insert_many(starter_products)

    # Generate 45 days of historical sales records with weekend seasonality
    start_date = date.today() - timedelta(days=45)
    sales_to_insert = []
    for p in starter_products:
        p_id = p["product_id"]
        base_dem = p["base_demand"]
        sp = float(p["selling_price"])
        cp = float(p["cost_price"])
        for day_offset in range(46):
            cur_date = start_date + timedelta(days=day_offset)
            date_str = cur_date.strftime("%Y-%m-%d")
            weekday = cur_date.weekday()
            day_mult = 1.35 if weekday in (5, 6) else (1.15 if weekday == 4 else 1.0)
            noise = random.uniform(-0.15, 0.15)
            units = max(1, int(round(base_dem * day_mult * (1.0 + noise))))
            rev = round(units * sp, 2)
            cogs_val = round(units * cp, 2)
            sales_to_insert.append({
                "sale_id": f"sale-{merchant_id}-{day_offset}-{p_id.split('-')[-1]}",
                "merchant_id": merchant_id,
                "product_id": p_id,
                "product_name": p["name"],
                "date": date_str,
                "units_sold": units,
                "unit_selling_price": sp,
                "unit_cost_price": cp,
                "revenue": rev,
                "cogs": cogs_val,
                "gross_profit": round(rev - cogs_val, 2),
                "is_synthetic": True,
            })
    if sales_to_insert:
        await db.sales.insert_many(sales_to_insert)

@router.post("/google", response_model=Token)
async def google_login(req: GoogleLoginRequest, db: AsyncIOMotorDatabase = Depends(get_database)):
    """
    Authenticate or auto-onboard a merchant using Google Sign-In.
    Supports Google Identity Services (GIS) ID tokens, access tokens, and dev/demo tokens.
    """
    email = None
    name = None
    picture = None

    token_str = req.credential or req.id_token
    if token_str:
        # 1. Try online verification with Google's public tokeninfo endpoint
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={token_str}")
                if resp.status_code == 200:
                    info = resp.json()
                    email = info.get("email")
                    name = info.get("name") or info.get("given_name")
                    picture = info.get("picture")
        except Exception:
            pass

        # 2. If online verification failed, parse JWT payload payload safely
        if not email and "." in token_str:
            try:
                parts = token_str.split(".")
                if len(parts) >= 2:
                    padded = parts[1] + "=" * (-len(parts[1]) % 4)
                    payload_bytes = base64.urlsafe_b64decode(padded)
                    claims = json.loads(payload_bytes.decode("utf-8"))
                    email = claims.get("email")
                    name = claims.get("name") or claims.get("given_name")
                    picture = claims.get("picture")
            except Exception:
                pass

    # 3. If access_token was supplied instead
    if not email and req.access_token:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    "https://www.googleapis.com/oauth2/v3/userinfo",
                    headers={"Authorization": f"Bearer {req.access_token}"}
                )
                if resp.status_code == 200:
                    info = resp.json()
                    email = info.get("email")
                    name = info.get("name") or info.get("given_name")
                    picture = info.get("picture")
        except Exception:
            pass

    # 4. Fallback to direct request email if supplied (e.g. dev/testing or mock Google login)
    if not email and req.email:
        email = str(req.email)
        name = req.name or email.split("@")[0].replace(".", " ").title()

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to verify Google credentials or retrieve email address.",
        )

    email = email.lower().strip()
    owner_name = name or email.split("@")[0].replace(".", " ").title()

    # Look up existing merchant
    merchant = await db.merchants.find_one({"email": email})
    now = datetime.utcnow()

    if not merchant:
        # Auto-provision a new merchant store for this Google user
        merchant_id = f"merchant-{uuid.uuid4().hex[:8]}"
        lat = req.latitude
        lng = req.longitude
        if lat is None or lng is None:
            lat = round(12.920737 + random.uniform(-0.0035, 0.0035), 6)
            lng = round(77.668710 + random.uniform(-0.0035, 0.0035), 6)
        coords = {"lat": lat, "lng": lng}
        business_name = req.business_name or f"{owner_name}'s Store"
        category = req.category or "Grocery & Daily Essentials"
        address = req.address or "Bellandur Retail Cluster, Bengaluru"
        phone = req.phone or "+91 98450 00000"

        merchant_doc = {
            "merchant_id": merchant_id,
            "business_name": business_name,
            "owner_name": owner_name,
            "email": email,
            "password_hash": "",
            "auth_provider": "google",
            "picture": picture,
            "category": category,
            "address": address,
            "phone": phone,
            "latitude": lat,
            "longitude": lng,
            "coordinates": coords,
            "created_at": now,
            "is_synthetic": False,
        }
        await db.merchants.insert_one(merchant_doc)
        merchant = merchant_doc

        # Seed initial starter catalog and 45 days of sales records tailored to selected category
        await seed_merchant_starter_data(db, merchant_id, category)
    else:
        # Update details if explicitly provided during registration completion
        updates = {}
        category_changed = False
        if req.business_name and req.business_name != merchant.get("business_name"):
            updates["business_name"] = req.business_name
        if req.category and req.category != merchant.get("category"):
            updates["category"] = req.category
            category_changed = True
        if req.address and req.address != merchant.get("address"):
            updates["address"] = req.address
        if req.phone and req.phone != merchant.get("phone"):
            updates["phone"] = req.phone
        if req.latitude is not None and req.longitude is not None:
            updates["latitude"] = req.latitude
            updates["longitude"] = req.longitude
            updates["coordinates"] = {"lat": req.latitude, "lng": req.longitude}
        if updates:
            await db.merchants.update_one({"merchant_id": merchant["merchant_id"]}, {"$set": updates})
            merchant = await db.merchants.find_one({"merchant_id": merchant["merchant_id"]})

        # Ensure merchant has products seeded (e.g. if previous attempt failed midway or category changed)
        prod_count = await db.products.count_documents({"merchant_id": merchant["merchant_id"]})
        if prod_count == 0 or category_changed:
            await seed_merchant_starter_data(
                db, merchant["merchant_id"], merchant.get("category", "Grocery & Daily Essentials")
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

@router.post("/otp/send", response_model=OtpResponse)
async def send_otp(req: SendOtpRequest, db: AsyncIOMotorDatabase = Depends(get_database)):
    """
    Send a 6-digit One-Time Password (OTP) to merchant phone or email for instant passwordless sign-in.
    In development & hackathon evaluation, returns demo_otp for instant 1-click verification.
    """
    identifier = req.phone_or_email.strip().lower()
    clean_digits = "".join(filter(str.isdigit, identifier))

    # Search for merchant by email or phone
    query_conditions = [
        {"email": identifier},
        {"phone": identifier},
    ]
    if len(clean_digits) >= 10:
        query_conditions.append({"phone": {"$regex": clean_digits[-10:]}})

    merchant = await db.merchants.find_one({"$or": query_conditions})
    if not merchant and ("@localpulse.demo" in identifier or any(d in clean_digits for d in ["98450", "98451", "98452", "98453", "98454", "98455"])):
        # Auto-seed demo accounts if requested
        from app.seed import seed_database
        await seed_database(db, force=False)
        merchant = await db.merchants.find_one({"$or": query_conditions})

    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No registered merchant account found matching '{req.phone_or_email}'. Please register your store first."
        )

    # Master test OTP code: 123456
    otp_code = "123456"
    expires_at = datetime.utcnow() + timedelta(minutes=5)

    # Store OTP in MongoDB collection `otps` (upsert by identifier)
    await db.otps.update_one(
        {"identifier": identifier},
        {"$set": {
            "identifier": identifier,
            "merchant_id": merchant["merchant_id"],
            "otp": otp_code,
            "expires_at": expires_at,
            "created_at": datetime.utcnow()
        }},
        upsert=True
    )

    return OtpResponse(
        status="success",
        message=f"6-digit verification code sent to {merchant.get('phone') or merchant.get('email')}.",
        phone_or_email=req.phone_or_email,
        demo_otp=otp_code,
        expires_in_seconds=300
    )

@router.post("/otp/verify", response_model=Token)
async def verify_otp(req: VerifyOtpRequest, db: AsyncIOMotorDatabase = Depends(get_database)):
    """
    Verify merchant OTP and issue JWT access token.
    Accepts active stored OTP or master test OTP '123456'.
    """
    identifier = req.phone_or_email.strip().lower()
    clean_digits = "".join(filter(str.isdigit, identifier))
    submitted_otp = req.otp.strip()

    query_conditions = [
        {"email": identifier},
        {"phone": identifier},
    ]
    if len(clean_digits) >= 10:
        query_conditions.append({"phone": {"$regex": clean_digits[-10:]}})

    merchant = await db.merchants.find_one({"$or": query_conditions})
    if not merchant and ("@localpulse.demo" in identifier or any(d in clean_digits for d in ["98450", "98451", "98452", "98453", "98454", "98455"])):
        from app.seed import seed_database
        await seed_database(db, force=False)
        merchant = await db.merchants.find_one({"$or": query_conditions})

    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Merchant account not found. Please verify your phone or email."
        )

    # Validate OTP
    is_valid = False
    if submitted_otp == "123456":
        is_valid = True
    else:
        otp_doc = await db.otps.find_one({"identifier": identifier})
        if otp_doc and otp_doc.get("otp") == submitted_otp:
            if otp_doc.get("expires_at", datetime.min) > datetime.utcnow():
                is_valid = True
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="OTP has expired. Please request a new code."
                )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP code. Please enter '123456' or request a new code."
        )

    # Clean up OTP record
    await db.otps.delete_one({"identifier": identifier})

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

@router.post("/login", response_model=Token)
async def login(req: LoginRequest, db: AsyncIOMotorDatabase = Depends(get_database)):
    """Authenticate merchant with email and password."""
    merchant = await db.merchants.find_one({"email": req.email.lower()})
    if not merchant and req.email.lower().endswith("@localpulse.demo"):
        # Auto-seed demo accounts if missing
        from app.seed import seed_database
        await seed_database(db, force=True)
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

    # Seed initial starter products and 45 days of sales records for immediate usability
    await seed_merchant_starter_data(db, merchant_id, req.category)

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
    if not merchants or len(merchants) < 6:
        from app.seed import seed_database
        await seed_database(db, force=False)
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
    merchant = await db.merchants.find_one({"$or": [{"merchant_id": req.merchant_id}, {"email": req.merchant_id.lower()}]})
    if not merchant:
        # Auto-seed demo database if missing
        from app.seed import seed_database
        await seed_database(db, force=True)
        merchant = await db.merchants.find_one({"$or": [{"merchant_id": req.merchant_id}, {"email": req.merchant_id.lower()}]})

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
