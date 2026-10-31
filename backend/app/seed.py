import random
from datetime import datetime, timedelta, date
from app.core.security import get_password_hash

MERCHANTS_DATA = [
    {
        "merchant_id": "merchant-001",
        "business_name": "Sharma Kirana & General Store",
        "owner_name": "Ramesh Sharma",
        "email": "sharma.kirana@localpulse.demo",
        "category": "Grocery & Daily Essentials",
        "address": "Shop 14, 12th Main Road, HAL 2nd Stage, Indiranagar, Bengaluru",
        "phone": "+91 98450 12345",
        "latitude": 12.920737,
        "longitude": 77.668710,
        "coordinates": {"lat": 12.920737, "lng": 77.668710},
        "default_password": "password123",
        "products": [
            {
                "product_id": "prod-001-atta",
                "name": "Aashirvaad Shudh Chakki Atta 5kg",
                "category": "Flour & Grains",
                "cost_price": 230.0,
                "selling_price": 275.0,
                "current_stock": 24,
                "reorder_threshold": 15,
                "unit": "packs",
                "base_demand": 8.0,
            },
            {
                "product_id": "prod-001-salt",
                "name": "Tata Salt Vacuum Evaporated Iodized 1kg",
                "category": "Spices & Seasoning",
                "cost_price": 22.0,
                "selling_price": 28.0,
                "current_stock": 65,
                "reorder_threshold": 20,
                "unit": "packs",
                "base_demand": 14.0,
            },
            {
                "product_id": "prod-001-milk",
                "name": "Amul Taaza Homogenised Toned Milk 1L",
                "category": "Dairy",
                "cost_price": 66.0,
                "selling_price": 74.0,
                "current_stock": 9,  # Low stock warning trigger!
                "reorder_threshold": 25,
                "unit": "cartons",
                "base_demand": 22.0,
            },
            {
                "product_id": "prod-001-oil",
                "name": "Fortune Sunlite Refined Sunflower Oil 1L",
                "category": "Edible Oils",
                "cost_price": 125.0,
                "selling_price": 155.0,
                "current_stock": 28,
                "reorder_threshold": 15,
                "unit": "bottles",
                "base_demand": 7.0,
            },
            {
                "product_id": "prod-001-tea",
                "name": "Brooke Bond Red Label Natural Care Tea 500g",
                "category": "Beverages",
                "cost_price": 260.0,
                "selling_price": 310.0,
                "current_stock": 14,
                "reorder_threshold": 12,
                "unit": "packs",
                "base_demand": 6.0,
            },
            {
                "product_id": "prod-001-rice",
                "name": "India Gate Basmati Rice Feast Rozzana 1kg",
                "category": "Flour & Grains",
                "cost_price": 95.0,
                "selling_price": 125.0,
                "current_stock": 38,
                "reorder_threshold": 15,
                "unit": "bags",
                "base_demand": 9.0,
            },
        ],
    },
    {
        "merchant_id": "merchant-002",
        "business_name": "Chai Point & Baker's Corner",
        "owner_name": "Priya Nair",
        "email": "priya.bakery@localpulse.demo",
        "category": "Cafe & Bakery",
        "address": "Shop 4, 100ft Road, Indiranagar, Bengaluru",
        "phone": "+91 98451 23456",
        "latitude": 12.923120,
        "longitude": 77.666950,
        "coordinates": {"lat": 12.923120, "lng": 77.666950},
        "default_password": "password123",
        "products": [
            {
                "product_id": "prod-002-sourdough",
                "name": "Artisan Country Sourdough Loaf",
                "category": "Bakery",
                "cost_price": 90.0,
                "selling_price": 160.0,
                "current_stock": 14,
                "reorder_threshold": 8,
                "unit": "loaves",
                "base_demand": 10.0,
            },
            {
                "product_id": "prod-002-chai",
                "name": "Signature Malabar Spiced Chai Blend 250g",
                "category": "Beverages",
                "cost_price": 110.0,
                "selling_price": 190.0,
                "current_stock": 42,
                "reorder_threshold": 15,
                "unit": "pouches",
                "base_demand": 12.0,
            },
            {
                "product_id": "prod-002-cookies",
                "name": "Dark Chocolate Sea Salt Cookies Box (6pc)",
                "category": "Confectionery",
                "cost_price": 120.0,
                "selling_price": 220.0,
                "current_stock": 19,
                "reorder_threshold": 10,
                "unit": "boxes",
                "base_demand": 14.0,
            },
            {
                "product_id": "prod-002-cake",
                "name": "Banana Walnut Teacake Slice",
                "category": "Bakery",
                "cost_price": 45.0,
                "selling_price": 95.0,
                "current_stock": 6,  # Low stock!
                "reorder_threshold": 12,
                "unit": "slices",
                "base_demand": 15.0,
            },
        ],
    },
    {
        "merchant_id": "merchant-003",
        "business_name": "Green Valley Organic Produce",
        "owner_name": "Vikram Patel",
        "email": "greenvalley@localpulse.demo",
        "category": "Fresh Fruits & Vegetables",
        "address": "Plot 88, CMH Road, Indiranagar, Bengaluru",
        "phone": "+91 98452 34567",
        "latitude": 12.926850,
        "longitude": 77.665320,
        "coordinates": {"lat": 12.926850, "lng": 77.665320},
        "default_password": "password123",
        "products": [
            {
                "product_id": "prod-003-salad",
                "name": "Hydroponic Crisp Salad Greens Box 250g",
                "category": "Organic Vegetables",
                "cost_price": 60.0,
                "selling_price": 120.0,
                "current_stock": 15,
                "reorder_threshold": 10,
                "unit": "boxes",
                "base_demand": 11.0,
            },
            {
                "product_id": "prod-003-apple",
                "name": "Himachal Royal Delicious Apples 1kg",
                "category": "Fresh Fruits",
                "cost_price": 130.0,
                "selling_price": 190.0,
                "current_stock": 25,
                "reorder_threshold": 15,
                "unit": "kg",
                "base_demand": 16.0,
            },
            {
                "product_id": "prod-003-avocado",
                "name": "Fresh Hass Avocados (Twin Pack)",
                "category": "Fresh Fruits",
                "cost_price": 140.0,
                "selling_price": 240.0,
                "current_stock": 8,  # Low stock!
                "reorder_threshold": 12,
                "unit": "packs",
                "base_demand": 9.0,
            },
        ],
    },
    {
        "merchant_id": "merchant-004",
        "business_name": "Modern Threads & Apparel",
        "owner_name": "Anita Roy",
        "email": "modernthreads@localpulse.demo",
        "category": "Fashion & Textiles",
        "address": "Building 5, 12th Main, Indiranagar, Bengaluru",
        "phone": "+91 98453 45678",
        "latitude": 12.922180,
        "longitude": 77.670550,
        "coordinates": {"lat": 12.922180, "lng": 77.670550},
        "default_password": "password123",
        "products": [
            {
                "product_id": "prod-004-kurta",
                "name": "Handloom Pure Khadi Cotton Kurta",
                "category": "Apparel",
                "cost_price": 480.0,
                "selling_price": 950.0,
                "current_stock": 24,
                "reorder_threshold": 10,
                "unit": "pieces",
                "base_demand": 4.0,
            },
            {
                "product_id": "prod-004-dupatta",
                "name": "Handcrafted Pochampally Ikat Dupatta",
                "category": "Apparel",
                "cost_price": 220.0,
                "selling_price": 499.0,
                "current_stock": 18,
                "reorder_threshold": 8,
                "unit": "pieces",
                "base_demand": 5.0,
            },
        ],
    },
    {
        "merchant_id": "merchant-005",
        "business_name": "Sanjeevani Ayurvedic Wellness",
        "owner_name": "Dr. Alok Gupta",
        "email": "sanjeevani@localpulse.demo",
        "category": "Health & Wellness",
        "address": "Shop 21, 6th Cross, Indiranagar, Bengaluru",
        "phone": "+91 98454 56789",
        "latitude": 12.918950,
        "longitude": 77.666820,
        "coordinates": {"lat": 12.918950, "lng": 77.666820},
        "default_password": "password123",
        "products": [
            {
                "product_id": "prod-005-chyawanprash",
                "name": "Sanjeevani Pure Amla Chyawanprash 1kg",
                "category": "Ayurveda",
                "cost_price": 280.0,
                "selling_price": 420.0,
                "current_stock": 22,
                "reorder_threshold": 10,
                "unit": "jars",
                "base_demand": 5.0,
            },
            {
                "product_id": "prod-005-oil",
                "name": "Cold-Pressed Pure Virgin Coconut Oil 500ml",
                "category": "Organic Wellness",
                "cost_price": 160.0,
                "selling_price": 260.0,
                "current_stock": 29,
                "reorder_threshold": 12,
                "unit": "bottles",
                "base_demand": 7.0,
            },
        ],
    },
    {
        "merchant_id": "merchant-006",
        "business_name": "Anand Sweets & Savories",
        "owner_name": "Anand Joshi",
        "email": "anandsweets@localpulse.demo",
        "category": "Traditional Sweets & Snacks",
        "address": "Ground Floor, 80ft Road, Indiranagar, Bengaluru",
        "phone": "+91 98455 67890",
        "latitude": 12.924890,
        "longitude": 77.671950,
        "coordinates": {"lat": 12.924890, "lng": 77.671950},
        "default_password": "password123",
        "products": [
            {
                "product_id": "prod-006-kajukatli",
                "name": "Royal Silver Foil Kaju Katli Box 500g",
                "category": "Traditional Sweets",
                "cost_price": 380.0,
                "selling_price": 580.0,
                "current_stock": 16,
                "reorder_threshold": 10,
                "unit": "boxes",
                "base_demand": 8.0,
            },
            {
                "product_id": "prod-006-mixture",
                "name": "Special Bengaluru Spicy Mixture 250g",
                "category": "Savories",
                "cost_price": 55.0,
                "selling_price": 110.0,
                "current_stock": 35,
                "reorder_threshold": 15,
                "unit": "packs",
                "base_demand": 14.0,
            },
        ],
    },
]

async def seed_database(db, force: bool = False):
    """Seed synthetic demo merchants, products, 90-day sales history, collaborations, and campaigns."""
    existing_merchants = await db.merchants.count_documents({})
    if existing_merchants > 0 and not force:
        return {"status": "skipped", "message": f"Database already contains {existing_merchants} merchants"}

    # Clear existing data if force
    if force:
        await db.merchants.delete_many({})
        await db.products.delete_many({})
        await db.sales.delete_many({})
        await db.inventory_movements.delete_many({})
        await db.collaborations.delete_many({})
        await db.campaigns.delete_many({})
        await db.campaign_redemptions.delete_many({})
        await db.copilot_conversations.delete_many({})
        await db.copilot_messages.delete_many({})
        await db.neighborhood_events.delete_many({})

    # Use deterministic PRNG
    rng = random.Random(42)
    today = date.today()
    start_date = today - timedelta(days=90)

    merchants_to_insert = []
    products_to_insert = []
    sales_to_insert = []
    movements_to_insert = []

    for m_data in MERCHANTS_DATA:
        m_id = m_data["merchant_id"]
        hashed_pwd = get_password_hash(m_data["default_password"])
        now_dt = datetime.utcnow()

        lat = m_data.get("latitude", 12.920737)
        lng = m_data.get("longitude", 77.668710)
        merchant_doc = {
            "merchant_id": m_id,
            "business_name": m_data["business_name"],
            "owner_name": m_data["owner_name"],
            "email": m_data["email"],
            "password_hash": hashed_pwd,
            "category": m_data["category"],
            "address": m_data["address"],
            "phone": m_data["phone"],
            "latitude": lat,
            "longitude": lng,
            "coordinates": m_data.get("coordinates", {"lat": lat, "lng": lng}),
            "created_at": now_dt - timedelta(days=95),
            "is_synthetic": True,
        }
        merchants_to_insert.append(merchant_doc)

        for p in m_data["products"]:
            p_id = p["product_id"]
            sp = float(p["selling_price"])
            # If product is targeted by active seed campaign, apply discount initially
            if p_id in ("prod-001-atta", "prod-001-oil"):
                eff_sp = round(sp * (1.0 - 0.08), 2)
                active_camp = "camp-001-festive"
            else:
                eff_sp = sp
                active_camp = None

            prod_doc = {
                "product_id": p_id,
                "merchant_id": m_id,
                "name": p["name"],
                "category": p["category"],
                "cost_price": float(p["cost_price"]),
                "selling_price": sp,
                "effective_selling_price": eff_sp,
                "active_campaign_id": active_camp,
                "current_stock": int(p["current_stock"]),
                "reorder_threshold": int(p["reorder_threshold"]),
                "unit": p["unit"],
                "created_at": now_dt - timedelta(days=92),
                "updated_at": now_dt,
                "is_synthetic": True,
            }
            products_to_insert.append(prod_doc)

            # Generate 90 days of daily sales
            base_dem = p["base_demand"]
            for day_offset in range(91):
                cur_date = start_date + timedelta(days=day_offset)
                date_str = cur_date.strftime("%Y-%m-%d")
                weekday = cur_date.weekday()  # 0=Monday, 5=Sat, 6=Sun

                # Weekday seasonality multiplier
                # Weekends (Sat, Sun) see higher foot traffic
                if weekday in (5, 6):
                    day_mult = 1.35
                elif weekday == 4:  # Friday
                    day_mult = 1.15
                elif weekday in (1, 2):  # Tue, Wed
                    day_mult = 0.90
                else:
                    day_mult = 1.0

                # Deterministic event lifts:
                # 1. Festival sale around day 45
                # 2. Local weekend street fair around day 75
                event_mult = 1.0
                if 43 <= day_offset <= 46:
                    event_mult = 1.55  # Festive spike
                elif 73 <= day_offset <= 75:
                    event_mult = 1.30  # Local carnival spike

                # Random gaussian noise
                noise = rng.gauss(0, 0.15)
                expected_units = max(1, int(round(base_dem * day_mult * event_mult * (1 + noise))))

                unit_selling = float(p["selling_price"])
                unit_cost = float(p["cost_price"])
                revenue = round(expected_units * unit_selling, 2)
                cogs = round(expected_units * unit_cost, 2)
                gross_profit = round(revenue - cogs, 2)

                sales_to_insert.append({
                    "merchant_id": m_id,
                    "product_id": p_id,
                    "product_name": p["name"],
                    "date": date_str,
                    "units_sold": expected_units,
                    "unit_selling_price": unit_selling,
                    "unit_cost_price": unit_cost,
                    "revenue": revenue,
                    "cogs": cogs,
                    "gross_profit": gross_profit,
                    "is_synthetic": True,
                })

            # Add an initial inventory restock audit log
            movements_to_insert.append({
                "movement_id": f"mov-{m_id}-{p_id}-init",
                "merchant_id": m_id,
                "product_id": p_id,
                "product_name": p["name"],
                "adjustment_type": "AUDIT_CORRECTION",
                "quantity_change": p["current_stock"],
                "stock_before": 0,
                "stock_after": p["current_stock"],
                "notes": "Initial inventory baseline verification",
                "created_at": now_dt - timedelta(days=1),
                "is_synthetic": True,
            })

    await db.merchants.insert_many(merchants_to_insert)
    await db.products.insert_many(products_to_insert)
    await db.sales.insert_many(sales_to_insert)
    await db.inventory_movements.insert_many(movements_to_insert)

    # Seed Initial Collaboration Proposal
    # Proposal between Sharma Kirana & Priya Nair's Bakery
    collab_doc = {
        "proposal_id": "collab-prop-001",
        "bundle_name": "Sunday Breakfast & Chai Heritage Combo",
        "bundle_description": "Pairing Brooke Bond Red Label Natural Care Tea (500g) with Baker's Corner Artisan Sourdough Loaf. Cross-promoted via QR vouchers.",
        "initiator_merchant_id": "merchant-001",
        "initiator_merchant_name": "Sharma Kirana & General Store",
        "initiator_product_id": "prod-001-tea",
        "initiator_product_name": "Brooke Bond Red Label Natural Care Tea 500g",
        "initiator_original_price": 310.0,
        "initiator_discount_pct": 10.0,
        "initiator_discounted_price": 279.0,
        "initiator_cost": 260.0,
        "initiator_margin_pct": 6.81,  # low margin note
        "initiator_approved": True,

        "partner_merchant_id": "merchant-002",
        "partner_merchant_name": "Chai Point & Baker's Corner",
        "partner_product_id": "prod-002-sourdough",
        "partner_product_name": "Artisan Country Sourdough Loaf",
        "partner_original_price": 160.0,
        "partner_discount_pct": 15.0,
        "partner_discounted_price": 136.0,
        "partner_cost": 90.0,
        "partner_margin_pct": 33.82,
        "partner_approved": False,  # Pending Priya Nair's review/approval!

        "original_bundle_price": 470.0,
        "discounted_bundle_price": 415.0,
        "effective_discount_pct": 11.7,
        "status": "PENDING_APPROVAL",
        "proposed_duration_days": 14,
        "created_at": datetime.utcnow() - timedelta(days=2),
        "updated_at": datetime.utcnow() - timedelta(days=2),
        "is_synthetic": True,
    }
    await db.collaborations.insert_one(collab_doc)

    # Seed an Active Campaign for Sharma Kirana
    camp_doc = {
        "campaign_id": "camp-001-festive",
        "merchant_id": "merchant-001",
        "title": "Weekend Essentials Value Push",
        "campaign_type": "Special Discount",
        "target_product_ids": ["prod-001-atta", "prod-001-oil"],
        "discount_pct": 8.0,
        "budget_allocated": 2500.0,
        "start_date": (today - timedelta(days=10)).strftime("%Y-%m-%d"),
        "end_date": (today + timedelta(days=4)).strftime("%Y-%m-%d"),
        "target_redemptions_goal": 60,
        "status": "ACTIVE",
        "created_at": datetime.utcnow() - timedelta(days=10),
        "is_synthetic": True,
    }
    await db.campaigns.insert_one(camp_doc)

    # Seed Simulated Redemptions for the Active Campaign
    redemptions = []
    for r_idx in range(38):
        r_day = today - timedelta(days=rng.randint(1, 9))
        redemptions.append({
            "redemption_id": f"red-{camp_doc['campaign_id']}-{r_idx+1:03d}",
            "campaign_id": camp_doc["campaign_id"],
            "merchant_id": "merchant-001",
            "redeemed_at": datetime.combine(r_day, datetime.min.time()) + timedelta(hours=rng.randint(9, 21), minutes=rng.randint(0, 59)),
            "order_value": round(rng.uniform(380.0, 520.0), 2),
            "discount_amount": round(rng.uniform(28.0, 42.0), 2),
            "estimated_cogs": round(rng.uniform(290.0, 390.0), 2),
            "is_simulated": True,
        })
    await db.campaign_redemptions.insert_many(redemptions)

    # Seed Neighborhood Events Calendar for Indiranagar Hub
    events_to_insert = [
        {
            "event_id": "event-001-diwali",
            "title": "Diwali Festival Shopping & Gifting Rush",
            "description": "Peak festive season shopping across Sarjapur / Bellandur corridor. Residents purchasing dry fruits, sweets, premium teas, and home essentials.",
            "start_date": (today + timedelta(days=1)).strftime("%Y-%m-%d"),
            "end_date": (today + timedelta(days=5)).strftime("%Y-%m-%d"),
            "location_name": "Bellandur-Sarjapur Main Road Retail Corridor",
            "coordinates": {"lat": 12.921500, "lng": 77.669200},
            "category_impacts": [
                {"category": "Traditional Sweets", "multiplier": 2.6, "projected_demand_change_pct": 160, "highlight_products": ["Kaju Katli", "Spicy Mixture"]},
                {"category": "Beverages", "multiplier": 1.9, "projected_demand_change_pct": 90, "highlight_products": ["Red Label Tea", "Malabar Chai"]},
                {"category": "Flour & Grains", "multiplier": 1.6, "projected_demand_change_pct": 60, "highlight_products": ["Chakki Atta", "Basmati Rice"]},
            ],
            "recommended_action": "Maintain buffer inventory of 50+ packs of Chakki Atta and sweet gift hampers. Run promotional bundle with nearby bakery.",
            "severity": "HIGH",
        },
        {
            "event_id": "event-002-payday",
            "title": "Tech Corridor Payday Weekend Surge",
            "description": "Monthly tech worker payroll credit cycle driving high discretionary evening footfall to local cafes, apparel boutiques, and gourmet grocery stores.",
            "start_date": (today + timedelta(days=3)).strftime("%Y-%m-%d"),
            "end_date": (today + timedelta(days=5)).strftime("%Y-%m-%d"),
            "location_name": "EcoSpace & Outer Ring Rd Tech District",
            "coordinates": {"lat": 12.923800, "lng": 77.667500},
            "category_impacts": [
                {"category": "Cafe & Bakery", "multiplier": 1.95, "projected_demand_change_pct": 95, "highlight_products": ["Artisan Sourdough", "Teacake Slices"]},
                {"category": "Apparel", "multiplier": 1.8, "projected_demand_change_pct": 80, "highlight_products": ["Khadi Kurtas", "Ikat Dupattas"]},
                {"category": "Beverages", "multiplier": 1.7, "projected_demand_change_pct": 70, "highlight_products": ["Specialty Chai Blend"]},
            ],
            "recommended_action": "Extend operating hours until 10:30 PM and offer bundled afternoon beverage vouchers with adjacent stores.",
            "severity": "MEDIUM",
        },
        {
            "event_id": "event-003-farmers",
            "title": "Weekend Organic Farmers & Artisan Market",
            "description": "Bi-weekly open-air market drawing over 2,500 health-conscious families for farm-fresh produce and artisan culinary items.",
            "start_date": (today + timedelta(days=7)).strftime("%Y-%m-%d"),
            "end_date": (today + timedelta(days=8)).strftime("%Y-%m-%d"),
            "location_name": "Bellandur Green Grounds & Lake Promenade",
            "coordinates": {"lat": 12.925500, "lng": 77.666000},
            "category_impacts": [
                {"category": "Fresh Fruits", "multiplier": 2.1, "projected_demand_change_pct": 110, "highlight_products": ["Hass Avocados", "Himachal Apples"]},
                {"category": "Organic Vegetables", "multiplier": 2.0, "projected_demand_change_pct": 100, "highlight_products": ["Hydroponic Salad Greens"]},
                {"category": "Organic Wellness", "multiplier": 1.7, "projected_demand_change_pct": 70, "highlight_products": ["Virgin Coconut Oil"]},
            ],
            "recommended_action": "Pre-pack twin avocados and 250g salad green boxes for quick cash-and-carry morning transactions.",
            "severity": "HIGH",
        },
        {
            "event_id": "event-004-langar",
            "title": "Guru Nanak Jayanti Community Langar Drive",
            "description": "Massive community kitchen meal distribution requiring bulk staples procurement.",
            "start_date": (today + timedelta(days=15)).strftime("%Y-%m-%d"),
            "end_date": (today + timedelta(days=15)).strftime("%Y-%m-%d"),
            "location_name": "Community Hall & Gurudwara Center",
            "coordinates": {"lat": 12.919200, "lng": 77.671500},
            "category_impacts": [
                {"category": "Flour & Grains", "multiplier": 2.3, "projected_demand_change_pct": 130, "highlight_products": ["Chakki Atta", "Basmati Rice"]},
                {"category": "Edible Oils", "multiplier": 2.1, "projected_demand_change_pct": 110, "highlight_products": ["Sunflower Oil 1L"]},
                {"category": "Spices & Seasoning", "multiplier": 1.8, "projected_demand_change_pct": 80, "highlight_products": ["Tata Salt 1kg"]},
            ],
            "recommended_action": "Place replenishment order 3 days prior with wholesale distributors to avoid stockouts on staple grains.",
            "severity": "HIGH",
        },
        {
            "event_id": "event-005-cricket",
            "title": "Bengaluru Cricket Screening & Match Weekend",
            "description": "High-attendance weekend sporting broadcast screening bringing sports fans and family groups to local neighborhood lounges.",
            "start_date": (today + timedelta(days=20)).strftime("%Y-%m-%d"),
            "end_date": (today + timedelta(days=21)).strftime("%Y-%m-%d"),
            "location_name": "Bellandur Sports Arena & Lounges",
            "coordinates": {"lat": 12.922800, "lng": 77.671000},
            "category_impacts": [
                {"category": "Savories", "multiplier": 2.25, "projected_demand_change_pct": 125, "highlight_products": ["Spicy Mixture", "Cookie Boxes"]},
                {"category": "Beverages", "multiplier": 2.15, "projected_demand_change_pct": 115, "highlight_products": ["Chai Packs", "Cold Drinks"]},
            ],
            "recommended_action": "Stock counter-top impulse snack racks with 250g spicy mixtures and chilled milk/beverage cartons.",
            "severity": "MEDIUM",
        },
        {
            "event_id": "event-006-wellness",
            "title": "Bengaluru Health & Ayurvedic Wellness Fair",
            "description": "Community holistic wellness exhibition featuring certified herbalists, organic dietary specialists, and preventative health coaches.",
            "start_date": (today + timedelta(days=23)).strftime("%Y-%m-%d"),
            "end_date": (today + timedelta(days=24)).strftime("%Y-%m-%d"),
            "location_name": "Kaikondrahalli Lake Recreation Grounds",
            "coordinates": {"lat": 12.917800, "lng": 77.668200},
            "category_impacts": [
                {"category": "Ayurveda", "multiplier": 2.4, "projected_demand_change_pct": 140, "highlight_products": ["Amla Chyawanprash"]},
                {"category": "Organic Wellness", "multiplier": 2.2, "projected_demand_change_pct": 120, "highlight_products": ["Cold-Pressed Virgin Coconut Oil"]},
            ],
            "recommended_action": "Highlight immunity benefits and display informative standees for Chyawanprash at storefront entrance.",
            "severity": "MEDIUM",
        },
        {
            "event_id": "event-007-carnival",
            "title": "Local MSME & Street Food Carnival",
            "description": "Pedestrian festival promoting small business shopping, street musicians, and neighborhood cross-store redemption vouchers.",
            "start_date": (today + timedelta(days=28)).strftime("%Y-%m-%d"),
            "end_date": (today + timedelta(days=30)).strftime("%Y-%m-%d"),
            "location_name": "Central Retail Boulevard",
            "coordinates": {"lat": 12.921200, "lng": 77.668500},
            "category_impacts": [
                {"category": "All Categories", "multiplier": 1.85, "projected_demand_change_pct": 85, "highlight_products": ["All Catalog Products"]},
            ],
            "recommended_action": "Set up active collaboration combo bundles with neighboring cafes and apparel shops to capture cross-traffic.",
            "severity": "HIGH",
        },
    ]
    await db.neighborhood_events.insert_many(events_to_insert)

    return {
        "status": "success",
        "merchants_seeded": len(merchants_to_insert),
        "products_seeded": len(products_to_insert),
        "sales_records_seeded": len(sales_to_insert),
        "collaborations_seeded": 1,
        "campaigns_seeded": 1,
        "neighborhood_events_seeded": len(events_to_insert),
    }
