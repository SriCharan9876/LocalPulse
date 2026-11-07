"""
Collaboration intelligence: which neighbouring shop to partner with, on which products,
at what discounts, and why.

Every possible pairing (one of my products x one of the partner's products) is scored on
real signals instead of a fixed category table:
  1. Customer link   - are these bought together? (tea + teacake yes, tea + kurta no)
  2. My stock        - does the bundle move my surplus? (never promote my low-stock items)
  3. Partner pull    - does their product sell fast enough to bring footfall?
  4. Price balance   - a Rs 28 item bundled with a Rs 1,800 item makes no sense
  5. Festival boost  - an upcoming major festival lifts demand for both products
  6. Distance        - closer partners are easier for customers (partner-level)

Discounts are computed so BOTH shops keep the 12% minimum margin (plus a small buffer),
then checked again with CollaborationService.validate_bundle_margins.

With an LLM key set, Gemini chooses among the already-validated candidate pairs and writes
the bundle name and pitch. All numbers (discounts, margins, scores) always come from code,
so the AI cannot propose an unsafe bundle. Without a key, the rule-based choice is used.
"""

import asyncio
import json
import logging
import math
import re
import time
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

from app.core.config import settings
from app.services.collaboration import collaboration_service
from app.services.forecasting import _key_words

logger = logging.getLogger(__name__)

MIN_MARGIN_PCT = collaboration_service.MIN_MARGIN_THRESHOLD_PCT  # 12%
MARGIN_BUFFER_PCT = 2.0          # keep at least 14% so small price changes don't break the rule
TARGET_SIDE_DISCOUNT_PCT = 10.0  # aim for ~10% off each side when margins allow
MIN_SIDE_DISCOUNT_PCT = 3.0      # below this a discount isn't worth advertising
# Stock rule, relative to each shop's own normal: a kirana typically holds ~3 days of stock, a
# fresh-produce shop ~1 day. An item is excluded if it's at/below its reorder level or holds
# less than 60% of its shop's typical (median) days of stock.
MIN_COVER_VS_SHOP = 0.6
FESTIVAL_LOOKAHEAD_DAYS = 21

# ── Product "facets": what kind of thing a product is, from its category and name ──
FACET_WORDS = {
    "tea": {"tea", "chai", "coffee", "beverage"},
    "bakery": {"bakery", "bread", "loaf", "sourdough", "cake", "teacake", "cookie", "biscuit",
               "confectionery", "rusk", "pastry", "bun", "slice"},
    "dairy": {"dairy", "milk", "curd", "paneer", "butter", "ghee", "yogurt", "yoghurt", "cheese"},
    "staple": {"flour", "atta", "grain", "rice", "dal", "pulse", "salt", "spice", "seasoning",
               "sugar", "basmati", "chakki"},
    "oil": {"edible"},  # "Edible Oils"; plain "oil" is decided below (cooking vs coconut/wellness)
    # Fruit and vegetables are bought for different reasons: vegetables go with cooking
    # staples, fruit goes with breakfast, wellness and gifting.
    "vegetable": {"vegetable", "green", "salad", "hydroponic", "leafy", "onion", "tomato", "potato"},
    "fruit": {"fruit", "apple", "avocado", "banana", "mango", "orange"},
    "sweets": {"sweet", "mithai", "katli", "ladoo", "savory", "savorie", "mixture", "namkeen",
               "snack", "traditional"},
    "wellness": {"ayurveda", "ayurvedic", "wellness", "chyawanprash", "amla", "herbal", "immunity",
                 "virgin", "pressed"},
    "apparel": {"apparel", "kurta", "dupatta", "saree", "textile", "fashion", "cotton", "handloom",
                "ikat", "khadi"},
}

# A bundle is suggested only if customers genuinely buy the two things together.
MIN_AFFINITY = 0.6

# Everyday pairs: (facet A, facet B) -> (how strongly they are bought together 0..1, theme, why)
AFFINITY = {
    frozenset({"tea", "bakery"}): (1.00, "Chai & Snack Combo",
                                   "Customers buying tea often pick up something to eat with it."),
    frozenset({"dairy", "bakery"}): (0.95, "Breakfast Basket",
                                     "Milk and fresh bakes are a classic morning purchase together."),
    frozenset({"dairy", "tea"}): (0.90, "Morning Chai Kit",
                                  "Every cup of chai needs milk; both are bought daily."),
    frozenset({"staple", "oil"}): (0.90, "Kitchen Staples Pack",
                                   "Flour, rice and cooking oil are restocked together."),
    frozenset({"tea", "sweets"}): (0.85, "Chai-Time Namkeen Pack",
                                   "Namkeen and sweets are the usual partners for evening chai."),
    frozenset({"staple", "vegetable"}): (0.80, "Daily Cooking Basket",
                                         "Rice or atta plus fresh vegetables covers a full home-cooked meal."),
    frozenset({"oil", "vegetable"}): (0.75, "Fresh Cooking Basket",
                                      "Fresh vegetables and cooking oil are bought for the same meals."),
    frozenset({"fruit", "wellness"}): (0.75, "Fresh & Wellness Pack",
                                       "Health-focused shoppers buy fresh fruit and wellness products together."),
    frozenset({"tea", "wellness"}): (0.70, "Immunity Tea Pack",
                                     "Tea drinkers are a natural audience for immunity products."),
    frozenset({"bakery", "sweets"}): (0.70, "Celebration Treats Box",
                                      "Bakes and mithai together suit celebrations and gifting."),
    frozenset({"vegetable", "wellness"}): (0.65, "Healthy Kitchen Pack",
                                           "Fresh greens and wellness products suit the same health-focused shopper."),
    frozenset({"dairy", "fruit"}): (0.65, "Healthy Breakfast Pack",
                                    "Milk and fresh fruit make a healthy breakfast basket."),
    frozenset({"dairy", "sweets"}): (0.60, "Mithai & Milk Pack",
                                     "Many sweets are made or served with milk at home."),
}

# Festival pairs: only suggested when an upcoming major festival boosts BOTH products.
# These are the combinations people actually buy for festivals (gifting, festive cooking).
FESTIVAL_AFFINITY = {
    frozenset({"sweets", "apparel"}): (0.90, "Festive Gifting Pack",
                                       "New clothes and a sweet box are the classic festival gift."),
    frozenset({"staple", "oil"}): (0.95, "Festive Cooking Pack",
                                   "Festive cooking needs atta, rice and oil in larger quantities."),
    frozenset({"sweets", "fruit"}): (0.80, "Festive Fruit & Mithai Hamper",
                                     "Fruit and mithai together are a popular festival gift and offering."),
    frozenset({"bakery", "sweets"}): (0.80, "Celebration Treats Box",
                                      "Bakes and mithai are bought together for festival gatherings."),
    frozenset({"dairy", "sweets"}): (0.75, "Festive Sweets & Milk Pack",
                                     "Festival sweets are made and served with milk."),
}

# In-memory cache for Gemini choices: key -> (timestamp, {partner_id: {...}})
_AI_CACHE: Dict[str, Tuple[float, dict]] = {}
AI_CACHE_SECONDS = 1800
AI_TIMEOUT_SECONDS = 10.0


def _facets(product: dict) -> set:
    # Category first: the name can mislead ("Dark Chocolate Sea Salt Cookies" is not a salt product)
    words = _key_words(product.get("category"))
    facets = {f for f, keys in FACET_WORDS.items() if words & keys}
    if not facets:
        words = _key_words(product.get("name"))
        facets = {f for f, keys in FACET_WORDS.items() if words & keys}
    # "oil": cooking oil is a kitchen staple partner; virgin / cold-pressed coconut oil is wellness
    if "oil" in words and "wellness" not in facets:
        facets.add("oil")
    return facets or {"other"}


def _affinity(a: dict, b: dict, festival_boosts_both: bool = False) -> Optional[Tuple[float, str, str]]:
    """How meaningful the pair is. None if they aren't bought together (or are the same kind)."""
    fa, fb = _facets(a), _facets(b)
    best = None
    tables = [AFFINITY] + ([FESTIVAL_AFFINITY] if festival_boosts_both else [])
    for x in fa:
        for y in fb:
            if x == y or "other" in (x, y):
                continue
            for table in tables:
                hit = table.get(frozenset({x, y}))
                if hit and (best is None or hit[0] > best[0]):
                    best = hit
    if best is None or best[0] < MIN_AFFINITY:
        return None
    return best


def _max_safe_discount(product: dict) -> float:
    """Largest whole % discount that keeps margin >= 12% + buffer."""
    sp = float(product.get("selling_price") or 0)
    cp = float(product.get("cost_price") or 0)
    if sp <= 0:
        return 0.0
    keep = (MIN_MARGIN_PCT + MARGIN_BUFFER_PCT) / 100.0
    d = 1.0 - cp / ((1.0 - keep) * sp)
    return max(0.0, math.floor(d * 100.0))


def _short(name: str) -> str:
    words = [w for w in re.sub(r"\(.*?\)", "", name).split() if not re.fullmatch(r"\d+[a-zA-Z]*", w)]
    return " ".join(words[:3]) or name


def _stock_ratio(p: dict) -> float:
    return float(p.get("current_stock") or 0) / max(1.0, float(p.get("reorder_threshold") or 10))


def _daily_units(sales: List[dict], product_id: str, days: int = 14) -> float:
    since = (date.today() - timedelta(days=days - 1)).isoformat()
    total = sum(int(s.get("units_sold") or 0) for s in sales
                if s.get("product_id") == product_id and (s.get("date") or "") >= since)
    return total / days


def _festival_for(a: dict, b: dict, me: dict, partner: dict, events: List[dict]) -> Optional[dict]:
    """An upcoming major festival (within 3 weeks) that boosts BOTH products."""
    today = date.today()
    horizon = (today + timedelta(days=FESTIVAL_LOOKAHEAD_DAYS)).isoformat()
    words_a = _key_words(a.get("category")) | _key_words(me.get("category"))
    words_b = _key_words(b.get("category")) | _key_words(partner.get("category"))
    for ev in events or []:
        start = ev.get("start_date") or ""
        if not (today.isoformat() <= (ev.get("end_date") or start) and start <= horizon):
            continue
        impacts = ev.get("category_impacts") or []
        hits_a = any(_key_words(i.get("category")) & words_a for i in impacts)
        hits_b = any(_key_words(i.get("category")) & words_b for i in impacts)
        if hits_a and hits_b:
            return ev
    return None


def _cover_days(p: dict, sales: List[dict]) -> float:
    v = _daily_units(sales, p["product_id"])
    return (float(p.get("current_stock") or 0) / v) if v > 0 else 99.0


def _median(values: List[float]) -> float:
    vals = sorted(values)
    if not vals:
        return 0.0
    mid = len(vals) // 2
    return vals[mid] if len(vals) % 2 else (vals[mid - 1] + vals[mid]) / 2


def _evaluate_pair(a: dict, b: dict, me: dict, partner: dict, partner_sales_max: float,
                   sales: List[dict], events: List[dict], my_typical_cover: float) -> Optional[dict]:
    """Score one (my product, partner product) pairing. None if it isn't meaningful or safe."""
    # 1. Must be something customers genuinely buy together (festival pairs only when an
    #    upcoming major festival boosts both products)
    festival = _festival_for(a, b, me, partner, events)
    fit = _affinity(a, b, festival_boosts_both=festival is not None)
    if fit is None:
        return None
    affinity, theme, why = fit

    max_a, max_b = _max_safe_discount(a), _max_safe_discount(b)
    da = min(TARGET_SIDE_DISCOUNT_PCT, max_a)
    db = min(TARGET_SIDE_DISCOUNT_PCT, max_b)
    da = da if da >= MIN_SIDE_DISCOUNT_PCT else 0.0
    db = db if db >= MIN_SIDE_DISCOUNT_PCT else 0.0
    if da == 0 and db == 0:
        return None  # neither side can afford a discount worth advertising

    # Never push extra demand onto my own item if it's low or about to run out
    ratio_a = _stock_ratio(a)
    cover_a = _cover_days(a, sales)
    typical = my_typical_cover if my_typical_cover > 0 else cover_a
    if ratio_a <= 1.0 or cover_a < MIN_COVER_VS_SHOP * typical:
        return None
    ratio_b = _stock_ratio(b)

    check = collaboration_service.validate_bundle_margins(
        initiator_product=a, initiator_discount_pct=da,
        partner_product=b, partner_discount_pct=db, bundle_name="check",
    )
    if not check.is_financially_viable:
        return None

    # More stock than this shop usually holds = surplus worth moving
    surplus_a = max(0.0, min(1.0, (cover_a / typical - 0.8) / 1.2)) if typical < 99 else 0.5
    partner_ok = 1.0 if ratio_b > 1.0 else 0.3  # partner low on stock -> weaker offer
    vel_b = _daily_units(sales, b["product_id"])
    pull_b = (vel_b / partner_sales_max) if partner_sales_max > 0 else 0.0
    pa, pb = float(a.get("selling_price") or 0), float(b.get("selling_price") or 0)
    balance = (min(pa, pb) / max(pa, pb)) if max(pa, pb) > 0 else 0.0
    price_score = 0.0 if balance < 0.08 else math.sqrt(balance)

    score = (0.45 * affinity + 0.15 * surplus_a + 0.10 * partner_ok + 0.10 * pull_b
             + 0.10 * price_score + 0.10 * (1.0 if festival else 0.0))
    if da == 0 or db == 0:
        score *= 0.85  # one shop carries the whole discount: less fair, less likely to be accepted

    if festival:
        fest_name = re.split(r"[/(]", festival.get("title", "Festival"))[0].strip()
        theme = theme if theme.startswith(fest_name) else f"{fest_name} {theme}"

    reasons = [why]
    stock_txt = f"{int(a.get('current_stock') or 0)} {a.get('unit', 'units')}"
    n = max(1, round(cover_a))
    cover_txt = f"about {n} day{'s' if n != 1 else ''} of sales" if cover_a < 99 else "no recent sales"
    reasons.append(
        f"Your {_short(a['name'])} has {stock_txt} ({cover_txt}), so the bundle helps move surplus stock."
        if cover_a >= 1.2 * typical else
        f"Your {_short(a['name'])} has enough stock for the offer ({stock_txt}, {cover_txt})."
    )
    if vel_b > 0:
        reasons.append(f"Their {_short(b['name'])} sells about {vel_b:.0f}/day, which brings steady footfall.")
    if festival:
        reasons.append(f"{festival.get('title')} ({festival.get('start_date')}) is expected to lift demand for both.")
    if da == 0:
        reasons.append(f"Your margin on {_short(a['name'])} is too thin to discount, so the offer comes from their side.")
    elif db == 0:
        reasons.append(f"Their margin on {_short(b['name'])} is too thin to discount, so the offer comes from your side.")
    reasons.append(
        f"{da:g}% off yours and {db:g}% off theirs keeps margins at {check.initiator_margin_pct:.0f}% and "
        f"{check.partner_margin_pct:.0f}% (minimum is {MIN_MARGIN_PCT:g}%)."
    )

    return {
        "score": round(score, 4),
        "theme": theme,
        "reasons": reasons,
        "initiator_product_id": a["product_id"],
        "initiator_product_name": a["name"],
        "initiator_discount_pct": da,
        "initiator_margin_pct": check.initiator_margin_pct,
        "partner_product_id": b["product_id"],
        "partner_product_name": b["name"],
        "partner_discount_pct": db,
        "partner_margin_pct": check.partner_margin_pct,
        "original_bundle_price": check.original_bundle_price,
        "discounted_bundle_price": check.discounted_bundle_price,
        "effective_bundle_discount_pct": check.effective_bundle_discount_pct,
        "festival": festival.get("title") if festival else None,
    }


def _rank_partner(me: dict, my_products: List[dict], partner: dict, partner_products: List[dict],
                  sales: List[dict], events: List[dict]) -> Tuple[List[dict], Dict[str, float]]:
    """All viable pairs with this partner, best first, plus a relevance score per partner product."""
    partner_sales_max = max([_daily_units(sales, p["product_id"]) for p in partner_products] or [0.0])
    my_typical_cover = _median([c for c in (_cover_days(p, sales) for p in my_products) if c < 99])
    pairs = []
    best_by_partner_product: Dict[str, float] = {}
    for a in my_products:
        for b in partner_products:
            ev = _evaluate_pair(a, b, me, partner, partner_sales_max, sales, events, my_typical_cover)
            if ev:
                pairs.append(ev)
                pid = b["product_id"]
                best_by_partner_product[pid] = max(best_by_partner_product.get(pid, 0.0), ev["score"])
    pairs.sort(key=lambda x: x["score"], reverse=True)
    return pairs, best_by_partner_product


async def _ai_choose(me: dict, candidates: Dict[str, dict], cache_only: bool = False) -> Dict[str, dict]:
    """
    Ask Gemini to choose the best candidate pair per partner and write the bundle name and
    pitch. candidates: {partner_id: {"partner": {...}, "pairs": [top validated pairs]}}.
    Returns {partner_id: {"index": i, "bundle_name": str, "pitch": str}}; {} on any problem.
    """
    if not (settings.LLM_API_KEY and settings.LLM_API_KEY.strip()) or not candidates:
        return {}
    if (settings.LLM_PROVIDER or "gemini").lower() != "gemini":
        return {}

    sig = json.dumps({pid: [(p["initiator_product_id"], p["partner_product_id"], p["initiator_discount_pct"],
                             p["partner_discount_pct"]) for p in c["pairs"]] for pid, c in candidates.items()},
                     sort_keys=True)
    key = f"{me.get('merchant_id')}|{date.today()}|{hash(sig)}"
    hit = _AI_CACHE.get(key)
    if hit and time.time() - hit[0] < AI_CACHE_SECONDS:
        return hit[1]
    if cache_only:
        return {}

    brief = []
    for pid, c in candidates.items():
        brief.append({
            "partner_id": pid,
            "partner": f"{c['partner']['business_name']} ({c['partner'].get('category', '')})",
            "options": [
                {"index": i, "my_product": p["initiator_product_name"], "their_product": p["partner_product_name"],
                 "my_discount_pct": p["initiator_discount_pct"], "their_discount_pct": p["partner_discount_pct"],
                 "facts": p["reasons"]}
                for i, p in enumerate(c["pairs"])
            ],
        })
    prompt = (
        "You help an Indian neighbourhood shop choose co-promotion bundles with nearby shops.\n"
        f"My shop: {me.get('business_name')} ({me.get('category')}).\n"
        "For each partner, choose the ONE option most likely to attract real customers who buy "
        "both items, using the facts given. Do not invent numbers.\n"
        "Return JSON only: a list of objects {\"partner_id\": str, \"index\": int, "
        "\"bundle_name\": str (max 5 words, catchy, no shop names), "
        "\"pitch\": str (one sentence for the partner shop owner, max 25 words)}.\n\n"
        + json.dumps(brief, ensure_ascii=False)
    )

    try:
        from google import genai
        from google.genai import types as genai_types
        client = genai.Client(api_key=settings.LLM_API_KEY)
        response = await asyncio.wait_for(
            client.aio.models.generate_content(
                model=settings.LLM_MODEL or "gemini-3.8-flash",
                contents=prompt,
                config=genai_types.GenerateContentConfig(temperature=0.2, response_mime_type="application/json"),
            ),
            timeout=AI_TIMEOUT_SECONDS,
        )
        data = json.loads(response.text or "[]")
        result = {}
        for item in data if isinstance(data, list) else []:
            pid = item.get("partner_id")
            idx = item.get("index")
            if pid in candidates and isinstance(idx, int) and 0 <= idx < len(candidates[pid]["pairs"]):
                result[pid] = {
                    "index": idx,
                    "bundle_name": str(item.get("bundle_name") or "").strip()[:60],
                    "pitch": str(item.get("pitch") or "").strip()[:220],
                }
        _AI_CACHE[key] = (time.time(), result)
        return result
    except Exception as e:  # no key / timeout / bad JSON / API error -> rules only
        from app.core.llm_monitor import is_gemini_rate_limit_error, record_gemini_rate_limit
        if is_gemini_rate_limit_error(e):
            record_gemini_rate_limit()
        logger.warning(f"AI collaboration choice unavailable ({e!r}); using rule-based suggestions.")
        return {}


async def suggest_partners(
    me: dict,
    merchants: List[dict],
    products_by_merchant: Dict[str, List[dict]],
    sales: List[dict],
    events: List[dict],
    distance_km: Dict[str, float],
    use_ai="yes",
) -> List[dict]:
    """
    use_ai: "yes" (ask Gemini if a key is set), "cache" (only reuse an earlier Gemini answer,
    never wait on a call) or "no".
    One suggestion per other merchant, best first:
      {merchant, score (0-100), theme, rationale, reasons, bundle (or None), ranked_products, source}
    """
    my_products = products_by_merchant.get(me["merchant_id"], [])
    suggestions = []
    for m in merchants:
        if m["merchant_id"] == me["merchant_id"]:
            continue
        partner_products = products_by_merchant.get(m["merchant_id"], [])
        pairs, relevance = _rank_partner(me, my_products, m, partner_products, sales, events)
        dist = distance_km.get(m["merchant_id"], 1.0)
        dist_score = max(0.0, min(1.0, 1.0 - dist / 2.0))
        best = pairs[0] if pairs else None
        score = (0.9 * best["score"] + 0.1 * dist_score) if best else 0.1 * dist_score
        ranked_products = sorted(partner_products, key=lambda p: relevance.get(p["product_id"], 0.0), reverse=True)
        suggestions.append({
            "merchant": m,
            "score": max(5, min(98, round(score * 100))),
            "pairs": pairs[:3],
            "bundle": best,
            "ranked_products": ranked_products,
            "distance_km": dist,
            "source": "LocalPulse rules",
        })

    # Optional AI step: choose among the validated top pairs and write the wording
    if use_ai in (True, "yes", "cache"):
        candidates = {s["merchant"]["merchant_id"]: {"partner": s["merchant"], "pairs": s["pairs"]}
                      for s in suggestions if s["pairs"]}
        choices = await _ai_choose(me, candidates, cache_only=(use_ai == "cache"))
        for s in suggestions:
            pick = choices.get(s["merchant"]["merchant_id"])
            if not pick:
                continue
            chosen = dict(s["pairs"][pick["index"]])
            if pick["bundle_name"]:
                chosen["bundle_name"] = pick["bundle_name"]
            if pick["pitch"]:
                chosen["pitch"] = pick["pitch"]
            s["bundle"] = chosen
            s["source"] = "Gemini-assisted"

    for s in suggestions:
        b = s["bundle"]
        if b:
            b.setdefault("bundle_name", b["theme"])
            b.setdefault(
                "pitch",
                f"{_short(b['initiator_product_name'])} + {_short(b['partner_product_name'])} for "
                f"₹{b['discounted_bundle_price']:,.0f} instead of ₹{b['original_bundle_price']:,.0f}.",
            )
            s["theme"] = b["theme"]
            s["rationale"] = " ".join(b["reasons"][:2])
            s["reasons"] = b["reasons"]
        else:
            s["theme"] = "No natural bundle"
            s["rationale"] = ("None of your products pair naturally with theirs (things customers buy together), "
                              "or the matching items are low on stock or margin. You can still build a bundle manually.")
            s["reasons"] = [s["rationale"]]

    suggestions.sort(key=lambda s: s["score"], reverse=True)
    return suggestions


async def load_suggestions(db, merchant: dict, use_ai="yes") -> List[dict]:
    """Load catalog, recent sales, festivals and distances, then rank partners for this merchant.
    Shared by /collaborations/discover and /neighborhood/merchants so both show the same advice."""
    from app.services.forecasting import load_relevant_events
    from app.services.occasions import calculate_haversine

    merchants = await db.merchants.find({}, {"password_hash": 0}).to_list(length=100)
    products = await db.products.find({}).to_list(length=1000)
    by_merchant: Dict[str, List[dict]] = {}
    for p in products:
        by_merchant.setdefault(p["merchant_id"], []).append(p)
    since = (date.today() - timedelta(days=13)).isoformat()
    sales = await db.sales.find({"date": {"$gte": since}}).to_list(length=None)
    events = await load_relevant_events(db, merchant)

    lat, lng = merchant.get("latitude"), merchant.get("longitude")
    distances = {}
    for m in merchants:
        try:
            distances[m["merchant_id"]] = calculate_haversine(float(lat), float(lng),
                                                              float(m.get("latitude")), float(m.get("longitude")))
        except (TypeError, ValueError):
            distances[m["merchant_id"]] = 1.0
    return await suggest_partners(merchant, merchants, by_merchant, sales, events, distances, use_ai=use_ai)
