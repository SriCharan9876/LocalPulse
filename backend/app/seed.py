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
    demo_ids = [m["merchant_id"] for m in MERCHANTS_DATA]
    demo_count = await db.merchants.count_documents({"merchant_id": {"$in": demo_ids}})
    if demo_count >= len(MERCHANTS_DATA) and not force:
        return {"status": "skipped", "message": f"Database already contains all {demo_count} demo merchants"}

    # If force reset requested, clean up all non-prebuilt user records
    if force:
        await db.merchants.delete_many({"merchant_id": {"$nin": demo_ids}})
        await db.products.delete_many({"merchant_id": {"$nin": demo_ids}})
        await db.sales.delete_many({"merchant_id": {"$nin": demo_ids}})
        await db.inventory_movements.delete_many({"merchant_id": {"$nin": demo_ids}})
        await db.collaborations.delete_many({"$or": [{"initiator_merchant_id": {"$nin": demo_ids}}, {"partner_merchant_id": {"$nin": demo_ids}}]})
        await db.campaigns.delete_many({"merchant_id": {"$nin": demo_ids}})
        await db.campaign_redemptions.delete_many({})
        await db.copilot_conversations.delete_many({})
        await db.copilot_messages.delete_many({})
        await db.merchant_occasion_insights.delete_many({})
        await db.otps.delete_many({})
        await db.neighborhood_events.delete_many({})

    # Clean existing demo records cleanly before re-inserting
    await db.merchants.delete_many({"merchant_id": {"$in": demo_ids}})
    await db.products.delete_many({"merchant_id": {"$in": demo_ids}})
    await db.sales.delete_many({"merchant_id": {"$in": demo_ids}})
    await db.inventory_movements.delete_many({"merchant_id": {"$in": demo_ids}})
    await db.collaborations.delete_many({"$or": [{"initiator_merchant_id": {"$in": demo_ids}}, {"partner_merchant_id": {"$in": demo_ids}}]})
    await db.campaigns.delete_many({"merchant_id": {"$in": demo_ids}})
    await db.campaign_redemptions.delete_many({"$or": [{"merchant_id": {"$in": demo_ids}}, {"campaign_id": "camp-001-festive"}]})
    await db.merchant_occasion_insights.delete_many({"merchant_id": {"$in": demo_ids}})

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

    # All-India occasions & festivals are loaded dynamically from live Google Calendar & API feeds.
    # No synthetic neighborhood events seeded into database.
    return {
        "status": "success",
        "merchants_seeded": len(merchants_to_insert),
        "products_seeded": len(products_to_insert),
        "sales_records_seeded": len(sales_to_insert),
        "collaborations_seeded": 1,
        "campaigns_seeded": 1,
        "events_source": "Live Google Calendar All-India Feed",
    }
