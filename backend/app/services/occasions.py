import math
import re
import time
import json
import asyncio
import logging
from datetime import datetime, date
from typing import List, Tuple, Optional, Dict
import httpx
from app.core.config import settings
from app.schemas.neighborhood import (
    NeighborhoodEvent,
    MerchantCoordinates,
    EventCategoryImpact,
)

logger = logging.getLogger("localpulse.occasions")

# In-memory cache for live events: (cached_events, source_name, timestamp)
_EVENTS_CACHE: Optional[Tuple[List[NeighborhoodEvent], str, float]] = None
CACHE_TTL_SECONDS = 3600 * 12  # Cache for 12 hours to stay well within free API limits (500/month)

def calculate_haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Returns distance in kilometers using the Haversine formula."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)

# Retail Demand Intelligence Rules for Indian Occasions & Festivals
OCCASION_RULES = [
    {
        "keywords": ["diwali", "deepavali", "naraka chaturdasi"],
        "severity": "HIGH",
        "impacts": [
            ("Sweets & Snacks", 2.8, 180, ["Kaju Katli", "Motichoor Ladoo", "Gulab Jamun", "Dry Fruit Gift Boxes"]),
            ("Apparel & Gifting", 2.5, 150, ["Kurta Sets", "Silk Sarees", "Brass Lamps", "Decorative Diyas"]),
            ("Dry Fruits & Groceries", 2.6, 160, ["Almonds & Cashews Box", "Anjeer", "Festive Puja Samagri"]),
        ],
        "action": "Procure 2.5x festive sweets and gift packaging 5 days ahead. Ensure Paytm Soundbox audio volume is maximized for loud evening store rushes.",
    },
    {
        "keywords": ["holi", "dhuleti", "choti holi", "holika"],
        "severity": "HIGH",
        "impacts": [
            ("Sweets & Confectionery", 2.4, 140, ["Mawa Gujiya", "Namkeen Mathri", "Malpua Mix"]),
            ("Beverages & Dairy", 2.2, 120, ["Thandai Syrup", "Full Cream Milk", "Packaged Fruit Juices"]),
            ("Personal Care", 1.9, 90, ["Coconut Oil", "Herbal Gulal", "Moisturizing Soaps"]),
        ],
        "action": "Wrap Paytm Soundbox & POS QR in protective transparent film against water/gulal. Stack Thandai bottles and Gujiya boxes near front billing counter.",
    },
    {
        "keywords": ["eid", "ramadan", "id-ul-fitr", "id-ul-zuha", "bakrid", "milad"],
        "severity": "HIGH",
        "impacts": [
            ("Bakery, Dairy & Sweets", 2.6, 160, ["Sheer Khurma Mix", "Roasted Vermicelli / Sevaya", "Condensed Milk"]),
            ("Dry Fruits & Fresh Foods", 2.4, 140, ["Medjool Dates", "Pistachios & Walnuts", "Fresh Mutton & Poultry"]),
            ("Apparel & Fragrance", 2.2, 120, ["Attar / Perfumes", "Kurta Pyjama", "Embroidered Dupattas"]),
        ],
        "action": "Keep double stock of vermicelli, dates, and milk pouches. Ensure QR soundbox battery is 100% charged for post-prayer checkout surges.",
    },
    {
        "keywords": ["dussehra", "dasara", "navratri", "durga puja", "maha saptami", "maha ashtami", "vijayadashami"],
        "severity": "HIGH",
        "impacts": [
            ("Sweets & Puja Essentials", 2.5, 150, ["Besan Ladoo", "Camphor & Agarbatti", "Pooja Flowers", "Coconuts"]),
            ("Fasting Staples (Vrat)", 2.3, 130, ["Sabudana", "Singhara Flour", "Sendha Namak (Rock Salt)"]),
            ("Ethnic Apparel", 2.1, 110, ["Chaniya Choli", "Traditional Dhoti Kurta", "Puja Accessories"]),
        ],
        "action": "Create a dedicated 'Navratri Vrat & Puja' display at the front aisle. Stock high quantities of Sabudana, dry fruits, and fresh flowers.",
    },
    {
        "keywords": ["ganesh chaturthi", "vinayaka chavithi"],
        "severity": "HIGH",
        "impacts": [
            ("Sweets & Modaks", 2.7, 170, ["Ukadiche Modak", "Fried Modaks", "Boondi Ladoo"]),
            ("Puja Samagri & Fruits", 2.4, 140, ["Durva Grass", "Hibiscus Flowers", "Bananas", "Peda Boxes"]),
        ],
        "action": "Pre-pack Modak sets in ₹100, ₹200, and ₹500 festive packs for quick QR checkout to reduce waiting line queues.",
    },
    {
        "keywords": ["raksha bandhan", "rakhi", "bhai duj"],
        "severity": "HIGH",
        "impacts": [
            ("Chocolates & Confectionery", 2.7, 170, ["Cadbury Celebrations Box", "Kaju Katli Boxes", "Assorted Chocolates"]),
            ("Gifts & Rakhis", 2.5, 150, ["Handcrafted Rakhis", "Greeting Cards", "Gift Hampers"]),
        ],
        "action": "Set up a dedicated standalone Rakhi & Sweets express billing queue with visible Paytm QR standee.",
    },
    {
        "keywords": ["pongal", "makar sankranti", "lohri", "bihu", "uttarayan"],
        "severity": "HIGH",
        "impacts": [
            ("Groceries & Traditional Sweets", 2.4, 140, ["Til Ladoo / Gajak", "Organic Jaggery (Gud)", "Raw Rice", "Chikki"]),
            ("Apparel & Kites", 2.1, 110, ["Festive Dhotis & Sarees", "Kites & Manja", "Clay Cooking Pots"]),
        ],
        "action": "Bundle jaggery and sesame seeds in ready combo bags. Highlight regional specialty sweets at store entrance.",
    },
    {
        "keywords": ["christmas", "new year"],
        "severity": "HIGH",
        "impacts": [
            ("Bakery & Confectionery", 2.5, 150, ["Rich Plum Cake", "Fruit Cakes", "Artisan Cookies", "Chocolates"]),
            ("Party Snacks & Beverages", 2.3, 130, ["Soft Drinks & Tonic", "Potato Crisps", "Party Poppers", "Paper Cups"]),
        ],
        "action": "Keep cold storage loaded with beverages and dairy. Display plum cakes and bakery treats in high-visibility front racks.",
    },
    {
        "keywords": ["republic day", "independence day", "gandhi jayanti"],
        "severity": "MEDIUM",
        "impacts": [
            ("Snacks & Quick Refreshments", 1.8, 80, ["Juices & Water Bottles", "Samosas & Puffs", "Tri-color Sweets"]),
            ("Convenience Retail", 1.6, 60, ["Tiranga Flags", "Car Dashboard Flags", "Snack Multipacks"]),
        ],
        "action": "Prepare for morning footfall after flag hoisting ceremonies in neighborhood societies and schools.",
    },
    {
        "keywords": ["onam", "vishu", "ugadi", "gudi padwa", "baisakhi", "maha shivratri", "janmashtami", "chhath puja"],
        "severity": "HIGH",
        "impacts": [
            ("Festival Groceries & Sweets", 2.4, 140, ["Special Grains & Flours", "Payasam Mix", "Ghee & Milk", "Mithai"]),
            ("Fresh Produce & Puja", 2.2, 120, ["Banana Leaves", "Fresh Coconuts", "Incense & Camphor"]),
        ],
        "action": "Order seasonal staples and fresh puja items 2 days prior. Run local WhatsApp broadcast offers on festive combo kits.",
    },
]

def enrich_occasion(
    title: str,
    raw_desc: str,
    start_date: str,
    end_date: str,
    event_idx: int,
    source_name: str,
    base_lat: float,
    base_lng: float,
) -> NeighborhoodEvent:
    """Enriches raw holiday data with retail category impacts, coordinates, and recommendations."""
    title_lower = title.lower()
    desc_lower = raw_desc.lower()

    matched_rule = None
    for rule in OCCASION_RULES:
        if any(k in title_lower or k in desc_lower for k in rule["keywords"]):
            matched_rule = rule
            break

    if matched_rule:
        severity = matched_rule["severity"]
        impacts = [
            EventCategoryImpact(
                category=cat,
                multiplier=mult,
                projected_demand_change_pct=pct,
                highlight_products=prods,
            )
            for cat, mult, pct, prods in matched_rule["impacts"]
        ]
        recommended_action = matched_rule["action"]
    else:
        # Default All-India Observance impact
        severity = "MEDIUM" if "holiday" in desc_lower or "jayanti" in title_lower else "LOW"
        impacts = [
            EventCategoryImpact(
                category="Daily Essentials & Groceries",
                multiplier=1.4,
                projected_demand_change_pct=40,
                highlight_products=["Packaged Snacks", "Beverages", "Dairy"],
            ),
            EventCategoryImpact(
                category="Retail Footfall",
                multiplier=1.3,
                projected_demand_change_pct=30,
                highlight_products=["Convenience Items"],
            ),
        ]
        recommended_action = f"Promote seasonal items on storefront for {title}. Monitor evening peak customer traffic."

    clean_desc = raw_desc
    if not clean_desc or "Observance To hide" in clean_desc:
        clean_desc = f"{title} — Celebrated nationwide across India with high family gatherings, festive purchases, and local retail footfall."

    return NeighborhoodEvent(
        event_id=f"occasion-{event_idx}-{re.sub(r'[^a-zA-Z0-9]', '', title)[:16].lower()}",
        title=title,
        description=clean_desc,
        start_date=start_date,
        end_date=end_date or start_date,
        location_name=None,
        coordinates=None,
        distance_km=None,
        category_impacts=impacts,
        recommended_action=recommended_action,
        severity=severity,
        source=source_name,
    )

async def fetch_calendarific_occasions(api_key: str, base_lat: float, base_lng: float) -> List[NeighborhoodEvent]:
    """Fetches real All-India occasions from Calendarific API using free API key."""
    current_year = datetime.now().year
    years = [current_year]
    # If late in year (Oct-Dec), also fetch next year
    if datetime.now().month >= 9:
        years.append(current_year + 1)

    all_holidays = []
    async with httpx.AsyncClient(timeout=8.0) as client:
        for y in years:
            url = f"https://calendarific.com/api/v2/holidays?api_key={api_key}&country=IN&year={y}"
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    holidays = data.get("response", {}).get("holidays", [])
                    all_holidays.extend(holidays)
                    logger.info(f"Retrieved {len(holidays)} All-India occasions for year {y} from Calendarific.")
                else:
                    logger.warning(f"Calendarific returned HTTP {resp.status_code}: {resp.text[:120]}")
            except Exception as e:
                logger.error(f"Error fetching from Calendarific for {y}: {e}")

    if not all_holidays:
        return []

    # Filter unique by (name, date)
    seen = set()
    events = []
    idx = 1
    for h in all_holidays:
        name = h.get("name", "").strip()
        date_obj = h.get("date", {})
        iso_date = date_obj.get("iso", "")
        if not iso_date:
            dt = date_obj.get("datetime", {})
            y, m, d = dt.get("year"), dt.get("month"), dt.get("day")
            if y and m and d:
                iso_date = f"{y:04d}-{m:02d}-{d:02d}"

        # Normalize date to YYYY-MM-DD
        iso_date = iso_date[:10]
        key = (name.lower(), iso_date)
        if not name or not iso_date or key in seen:
            continue
        seen.add(key)

        desc = h.get("description", "")
        types = ", ".join(h.get("type", []))
        if types:
            desc = f"[{types}] {desc}"

        ev = enrich_occasion(
            title=name,
            raw_desc=desc,
            start_date=iso_date,
            end_date=iso_date,
            event_idx=idx,
            source_name="Calendarific All-India API",
            base_lat=base_lat,
            base_lng=base_lng,
        )
        events.append(ev)
        idx += 1

    return events

async def fetch_google_calendar_occasions(base_lat: float, base_lng: float) -> List[NeighborhoodEvent]:
    """
    Fetches real All-India holidays & observances from Google Calendar's live public feed.
    Requires ZERO API keys, 100% free, updated continuously by Google.
    """
    url = "https://calendar.google.com/calendar/ical/en.indian%23holiday%40group.v.calendar.google.com/public/basic.ics"
    async with httpx.AsyncClient(timeout=8.0) as client:
        resp = await client.get(url, headers={"User-Agent": "LocalPulse/1.0"})
        if resp.status_code != 200:
            logger.warning(f"Google Calendar iCal returned {resp.status_code}")
            return []
        content = resp.text

    parsed_raw = []
    current: Dict[str, str] = {}
    for line in content.splitlines():
        if line.startswith("BEGIN:VEVENT"):
            current = {}
        elif line.startswith("SUMMARY:"):
            current["title"] = line.replace("SUMMARY:", "").strip()
        elif line.startswith("DESCRIPTION:"):
            current["description"] = line.replace("DESCRIPTION:", "").replace(r"\,", ",").replace(r"\n", " ").strip()
        elif line.startswith("DTSTART;VALUE=DATE:"):
            raw_d = line.replace("DTSTART;VALUE=DATE:", "").strip()
            if len(raw_d) >= 8:
                current["start_date"] = f"{raw_d[:4]}-{raw_d[4:6]}-{raw_d[6:8]}"
        elif line.startswith("DTEND;VALUE=DATE:"):
            raw_d = line.replace("DTEND;VALUE=DATE:", "").strip()
            if len(raw_d) >= 8:
                current["end_date"] = f"{raw_d[:4]}-{raw_d[4:6]}-{raw_d[6:8]}"
        elif line.startswith("END:VEVENT"):
            if "title" in current and "start_date" in current:
                parsed_raw.append(current)

    # Sort by date
    parsed_raw.sort(key=lambda x: x["start_date"])

    # Filter to current/recent and upcoming occasions
    today_iso = date.today().isoformat()
    current_year = date.today().year
    min_date = f"{current_year}-01-01"

    seen = set()
    events = []
    idx = 1
    for item in parsed_raw:
        s_date = item["start_date"]
        if s_date < min_date:
            continue
        title = item["title"]
        key = (title.lower(), s_date)
        if key in seen:
            continue
        seen.add(key)

        ev = enrich_occasion(
            title=title,
            raw_desc=item.get("description", ""),
            start_date=s_date,
            end_date=item.get("end_date", s_date),
            event_idx=idx,
            source_name="Google Calendar All-India",
            base_lat=base_lat,
            base_lng=base_lng,
        )
        events.append(ev)
        idx += 1

    return events

async def enrich_events_with_gemini(
    merchant: dict,
    events: List[NeighborhoodEvent],
    db = None,
) -> List[NeighborhoodEvent]:
    """
    Enriches Google Calendar occasions with customized retail actions, bundling ideas,
    and category impacts generated by Gemini using the merchant's real store catalog.
    Caches insights in MongoDB (db.merchant_occasion_insights) for fast response times.
    """
    if not merchant or not events:
        return events

    merchant_id = merchant.get("merchant_id")
    if not merchant_id:
        return events

    now_ts = time.time()
    cached_doc = None

    # 1. Check MongoDB cache (24-hour validity)
    if db is not None:
        try:
            cached_doc = await db.merchant_occasion_insights.find_one({"merchant_id": merchant_id})
        except Exception as e:
            logger.warning(f"Error reading occasion insights cache for {merchant_id}: {e}")

    if cached_doc and (now_ts - cached_doc.get("updated_at", 0) < 86400):
        insights_map = cached_doc.get("insights", {})
        for ev in events:
            key = ev.title.lower().strip()
            matched = insights_map.get(key)
            if not matched:
                for k, v in insights_map.items():
                    if k in key or key in k:
                        matched = v
                        break
            if matched:
                ev.recommended_action = matched.get("recommended_action", ev.recommended_action)
                ev.severity = matched.get("severity", ev.severity)
                if matched.get("category_impacts"):
                    ev.category_impacts = [
                        EventCategoryImpact(
                            category=c.get("category", ""),
                            multiplier=float(c.get("multiplier", 1.0)),
                            projected_demand_change_pct=int(c.get("projected_demand_change_pct", 0)),
                            highlight_products=c.get("highlight_products", [])
                        )
                        for c in matched.get("category_impacts", [])
                    ]
        logger.info(f"Loaded {len(insights_map)} cached Gemini occasion insights for {merchant_id}")
        return events

    # 2. Gather real catalog data for this merchant
    real_products = []
    if db is not None:
        try:
            p_cursor = db.products.find({"merchant_id": merchant_id}).limit(15)
            async for p in p_cursor:
                real_products.append({
                    "name": p.get("name"),
                    "stock": p.get("current_stock", 0),
                    "price": p.get("selling_price", 0),
                    "category": p.get("category", "General"),
                })
        except Exception as e:
            logger.warning(f"Error fetching products for merchant {merchant_id}: {e}")

    # Fallback to base events if no LLM key or no products in catalog
    if not settings.LLM_API_KEY or not real_products:
        return events

    # 3. Select top upcoming occasions (next 8 upcoming events)
    today_str = date.today().isoformat()
    target_occasions = [e for e in events if e.start_date >= today_str][:8]
    if not target_occasions:
        target_occasions = events[:8]

    prompt = f"""
You are LocalPulse AI, the hyper-local demand forecasting engine for Indian MSME store owners.
Merchant: {merchant.get('business_name', 'Local Store')} (Category: {merchant.get('category', 'Retail')})
Address: {merchant.get('address', 'Bengaluru, India')}

Real Store Catalog Inventory:
{json.dumps(real_products, indent=2)}

Upcoming Indian Occasions from Google Calendar:
{json.dumps([{"title": e.title, "date": e.start_date} for e in target_occasions], indent=2)}

For each occasion, generate tailored retail insights in a JSON array:
[
  {{
    "title": "Exact occasion title matching the list",
    "recommended_action": "Specific inventory advice, reorder recommendations, bundling tips, and Paytm Soundbox checkout rush preparation that explicitly references the merchant's real catalog items and current stock levels.",
    "severity": "HIGH",
    "category_impacts": [
      {{
        "category": "Matching category from their store",
        "multiplier": 2.4,
        "projected_demand_change_pct": 140,
        "highlight_products": ["Exact product names from the real catalog that will experience high demand"]
      }}
    ]
  }}
]
Return ONLY a valid JSON array.
"""

    def _call_gemini_sync():
        from google import genai
        from google.genai import types as genai_types
        client = genai.Client(api_key=settings.LLM_API_KEY)
        resp = client.models.generate_content(
            model=settings.LLM_MODEL or "gemini-3.8-flash",
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2
            )
        )
        return resp.text

    try:
        gemini_raw = await asyncio.wait_for(
            asyncio.to_thread(_call_gemini_sync),
            timeout=6.0
        )
        insights_list = json.loads(gemini_raw)

        insights_map = {}
        for item in insights_list:
            t = (item.get("title") or "").lower().strip()
            if t:
                insights_map[t] = item

        # Apply Gemini insights to events
        for ev in events:
            ev_title_lower = ev.title.lower().strip()
            matched = insights_map.get(ev_title_lower)
            if not matched:
                for k, v in insights_map.items():
                    if k in ev_title_lower or ev_title_lower in k:
                        matched = v
                        break

            if matched:
                ev.recommended_action = matched.get("recommended_action", ev.recommended_action)
                ev.severity = matched.get("severity", ev.severity)
                if matched.get("category_impacts"):
                    ev.category_impacts = [
                        EventCategoryImpact(
                            category=c.get("category", ""),
                            multiplier=float(c.get("multiplier", 1.0)),
                            projected_demand_change_pct=int(c.get("projected_demand_change_pct", 0)),
                            highlight_products=c.get("highlight_products", [])
                        )
                        for c in matched.get("category_impacts", [])
                    ]

        # 4. Save to MongoDB cache for instant future loads
        if db is not None:
            try:
                await db.merchant_occasion_insights.update_one(
                    {"merchant_id": merchant_id},
                    {"$set": {"insights": insights_map, "updated_at": now_ts}},
                    upsert=True
                )
                logger.info(f"Saved {len(insights_map)} Gemini occasion insights to cache for {merchant_id}")
            except Exception as e:
                logger.warning(f"Error persisting merchant_occasion_insights: {e}")

    except Exception as e:
        logger.warning(f"Gemini call timed out or failed ({e}), using instant real-catalog enrichment fallback.")
        # Fallback using real merchant products directly
        prod_names = [p["name"] for p in real_products[:4]]
        prod_summary_str = ", ".join(prod_names[:2]) if prod_names else "store staples"
        for ev in events:
            if not ev.category_impacts or not ev.category_impacts[0].highlight_products:
                matching_prods = [p["name"] for p in real_products if any(w in p["name"].lower() for w in ["oil", "atta", "rice", "milk", "tea", "sweet", "cake", "cookie"])]
                if not matching_prods:
                    matching_prods = prod_names[:3]
                ev.category_impacts = [
                    EventCategoryImpact(
                        category=merchant.get("category", "General Store"),
                        multiplier=2.2 if ev.severity == "HIGH" else 1.5,
                        projected_demand_change_pct=120 if ev.severity == "HIGH" else 50,
                        highlight_products=matching_prods[:3]
                    )
                ]
                ev.recommended_action = f"Festive demand surge for {ev.title}: Prioritize stock of your core items ({prod_summary_str}). Reorder high-velocity items 3 days in advance and ensure Paytm Soundbox is kept fully charged."

    return events

async def get_all_india_occasions(
    merchant: dict = None,
    merchant_lat: float = 12.920737,
    merchant_lng: float = 77.668710,
    merchant_category: str = "",
    db = None,
) -> Tuple[List[NeighborhoodEvent], str]:
    """
    Returns only the 1 single category of events: Real All-India Occasions & Festivals
    fetched directly from Google Calendar All-India and personalized using Gemini
    with the merchant's real store catalog.
    """
    global _EVENTS_CACHE
    now = time.time()

    # Check memory cache for base calendar events
    cached_events = None
    source_name = "Google Calendar All-India"
    if _EVENTS_CACHE and (now - _EVENTS_CACHE[2] < CACHE_TTL_SECONDS):
        cached_events = _EVENTS_CACHE[0]
        source_name = _EVENTS_CACHE[1]

    if not cached_events:
        try:
            events_found = await fetch_google_calendar_occasions(merchant_lat, merchant_lng)
            if events_found:
                source_name = "Google Calendar All-India"
                _EVENTS_CACHE = (events_found, source_name, now)
                cached_events = events_found
        except Exception as e:
            logger.error(f"Google Calendar live feed fetch failed: {e}")

    # Make a copy so merchant-specific enrichment doesn't mutate global base cache
    events = [ev.model_copy() for ev in (cached_events or [])]

    # Enrich with Gemini using real store inventory!
    if merchant:
        events = await enrich_events_with_gemini(merchant, events, db)

    # Sort chronologically
    events.sort(key=lambda x: x.start_date)

    return events, source_name
