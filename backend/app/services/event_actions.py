"""
Festival / occasion action plans for the Local Map & Events page.

Turns an occasion (e.g. Diwali on 8 Nov) into concrete, confirmable actions for this shop,
in the same draft format the copilot uses:
  - RESTOCK_INVENTORY drafts for products the occasion boosts, sized from the forecast
    with the occasion's uplift (enough to last through the occasion + reorder buffer)
  - one small CREATE_CAMPAIGN draft (festival offer), priced to stay above cost
  - partner bundle ideas from the collaboration suggestions

Nothing is applied here: the page shows the drafts and the merchant confirms each one,
which goes through /copilot/confirm-action and its safety checks.
"""

import re
from datetime import date, timedelta
from typing import Dict, List, Optional

from app.schemas.copilot import DraftAction
from app.services.copilot.guards import max_discount_above_cost, check_discount_vs_cost
from app.services.forecasting import forecasting_service, event_multiplier_for_day

RESTOCK_WINDOW_DAYS = 21      # further away than this: too early to order stock
MAX_RESTOCK_DRAFTS = 3
FESTIVAL_OFFER_MAX_PCT = 8.0  # festival offers stay small: demand is already high
OFFER_MARGIN_BUFFER = 3.0     # percentage points of margin kept above cost


def _short_title(title: str) -> str:
    return re.split(r"[/(]", title or "Festival")[0].strip() or "Festival"


def _short_name(name: str) -> str:
    words = [w for w in re.sub(r"\(.*?\)", "", name).split() if not re.fullmatch(r"\d+[a-zA-Z]*", w)]
    return " ".join(words[:3]) or name


def _fmt_day(d: date) -> str:
    return f"{d.strftime('%a')} {d.day} {d.strftime('%b')}"


def build_event_action_plan(
    event: dict,
    merchant: dict,
    products: List[dict],
    sales: List[dict],
    partner_suggestions: Optional[List[dict]] = None,
    next_occurrence: Optional[dict] = None,
) -> dict:
    today = date.today()
    title = event.get("title") or "Occasion"
    short = _short_title(title)
    try:
        start = date.fromisoformat(event.get("start_date"))
        end = date.fromisoformat(event.get("end_date") or event.get("start_date"))
    except (TypeError, ValueError):
        return {"event_title": title, "headline": "This occasion has no valid date.", "notes": [], "drafts": [],
                "ideas": [], "insights": []}

    days_until = (start - today).days
    plan = {"event_title": title, "start_date": start.isoformat(), "end_date": end.isoformat(),
            "days_until": days_until, "headline": "", "notes": [], "drafts": [], "ideas": [], "insights": []}

    # Which of my products does this occasion boost, and by how much?
    event_days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    affected = []
    for p in products:
        mult = max((event_multiplier_for_day(d, p.get("category", ""), merchant.get("category"), [event])[0]
                    for d in event_days), default=1.0)
        if mult > 1.0:
            affected.append((p, mult))

    if end < today:
        return _past_occasion_plan(plan, event, short, start, end, event_days, affected, merchant, products,
                                   sales, partner_suggestions, next_occurrence)

    when = "today" if days_until <= 0 else ("tomorrow" if days_until == 1 else f"in {days_until} days")
    is_major = (event.get("severity") or "").upper() == "HIGH"
    if not affected:
        plan["headline"] = f"{short} ({_fmt_day(start)}, {when}) isn't expected to change demand for your products much."
        plan["notes"].append("No restock or offer needed. Footfall may still rise, so keep best sellers visible.")
    else:
        names = ", ".join(_short_name(p["name"]) for p, _ in affected[:4])
        top_mult = max(m for _, m in affected)
        plan["headline"] = (f"{'' if is_major else 'Minor observance: '}{short} is {when} ({_fmt_day(start)}). "
                            f"{'Expect' if is_major else 'The calendar estimates'} up to {top_mult:g}x normal demand "
                            f"for {names}{' and more' if len(affected) > 4 else ''}.")
        if not is_major:
            plan["notes"].append(
                "Your regular forecast ignores minor observances. This plan applies the calendar's estimate, "
                "so treat the restock amounts as an upper limit."
            )

    # ── Restock drafts ──────────────────────────────────────────────────────
    restock_candidates = []
    if affected and days_until > RESTOCK_WINDOW_DAYS:
        order_by = start - timedelta(days=3)
        plan["notes"].append(
            f"It's too early to order stock. Come back around {_fmt_day(order_by)} "
            f"(3 days before) and the plan will size your restock."
        )
        block = _expected_demand_block(affected, sales, start, f"Expected demand on {short} ({_fmt_day(start)})")
        if block:
            plan["insights"].append(block)
    elif affected:
        horizon = max(1, min(RESTOCK_WINDOW_DAYS, (end - today).days + 1))
        for p, mult in affected:
            p_sales = [s for s in sales if s.get("product_id") == p["product_id"]]
            fc = forecasting_service.forecast_product(p, p_sales, horizon_days=horizon, events=[event],
                                                      merchant_category=merchant.get("category"))
            stock = int(p.get("current_stock") or 0)
            threshold = int(p.get("reorder_threshold") or 10)
            needed = fc.total_forecasted_units + threshold - stock
            festival_extra = sum(round(d.predicted_units * (1 - 1 / d.event_multiplier))
                                 for d in fc.daily_forecasts if d.event_multiplier > 1.0)
            restock_candidates.append((p, mult, needed, festival_extra, fc.total_forecasted_units, horizon))

        restock_candidates.sort(key=lambda x: x[3], reverse=True)  # biggest festival effect first
        for p, mult, needed, extra, total, horizon in restock_candidates:
            if len(plan["drafts"]) >= MAX_RESTOCK_DRAFTS:
                break
            unit = p.get("unit", "units")
            if needed <= 0:
                plan["notes"].append(
                    f"{_short_name(p['name'])}: current stock ({int(p.get('current_stock') or 0)} {unit}) already "
                    f"covers the forecast through {_fmt_day(end)}."
                )
                continue
            plan["drafts"].append(DraftAction(
                action_type="RESTOCK_INVENTORY",
                title=f"Stock up {p['name']} for {short}",
                description=(f"Add {needed} {unit}: forecast demand through {_fmt_day(end)} is {total} {unit} "
                             f"(about {extra} extra because of {short}), plus your reorder buffer."),
                payload={
                    "product_id": p["product_id"],
                    "product_name": p["name"],
                    "quantity": int(needed),
                    "adjustment_type": "RESTOCK",
                    "notes": f"{short} prep ({start.isoformat()}): {mult:g}x expected demand",
                },
            ).model_dump())

    # ── One small festival offer ────────────────────────────────────────────
    if affected and days_until <= RESTOCK_WINDOW_DAYS and not is_major:
        plan["notes"].append("No festival discount suggested: a minor observance doesn't justify cutting prices.")
    if affected and days_until <= RESTOCK_WINDOW_DAYS and is_major:
        # Prefer the most boosted product that still has margin room for a small offer
        offer_pick = None
        for p, mult in sorted(affected, key=lambda x: x[1], reverse=True):
            cap = max_discount_above_cost(p) - OFFER_MARGIN_BUFFER
            disc = float(int(min(FESTIVAL_OFFER_MAX_PCT, cap)))
            if disc >= 3 and check_discount_vs_cost(p, disc) is None:
                offer_pick = (p, disc)
                break
        if offer_pick:
            p, disc = offer_pick
            offer_start = max(today, start - timedelta(days=2))
            offer_title = f"{short} Special: {_short_name(p['name'])}"
            plan["drafts"].append(DraftAction(
                action_type="CREATE_CAMPAIGN",
                title=f"Festival offer: {disc:g}% off {_short_name(p['name'])}",
                description=(f"Run '{offer_title}' from {_fmt_day(offer_start)} to {_fmt_day(end)} to win "
                             f"{short} shoppers from nearby stores. {disc:g}% off keeps the price above cost."),
                payload={
                    "title": offer_title,
                    "campaign_type": "Festival Discount",
                    "target_product_ids": [p["product_id"]],
                    "discount_pct": disc,
                    "budget_allocated": 1000.0,
                    "start_date": offer_start.isoformat(),
                    "end_date": end.isoformat(),
                    "target_redemptions_goal": 50,
                },
            ).model_dump())
        else:
            plan["notes"].append("Margins on the boosted products are too thin for a festival discount; focus on stock.")

    # ── Partner idea ────────────────────────────────────────────────────────
    for s in partner_suggestions or []:
        b = s.get("bundle")
        if not b:
            continue
        # Only partners whose bundle product this occasion actually boosts
        partner_cat = s["merchant"].get("category")
        partner_prod = next((x for x in s.get("ranked_products", []) if x["product_id"] == b["partner_product_id"]), {})
        boosted = any(event_multiplier_for_day(d, partner_prod.get("category", ""), partner_cat, [event])[0] > 1.0
                      for d in event_days)
        if b.get("festival") == title or boosted:
            plan["ideas"].append({
                "text": (f"Bundle with {s['merchant']['business_name']} for {short}: "
                         f"{_short_name(b['initiator_product_name'])} + {_short_name(b['partner_product_name'])} "
                         f"({b['initiator_discount_pct']:g}% + {b['partner_discount_pct']:g}% off)."),
                "href": f"/neighborhood?partner={s['merchant']['merchant_id']}",
            })
        if len(plan["ideas"]) >= 2:
            break

    return plan



# ── Past occasions: review what happened, recover, and plan the next one ─────

RECENT_PAST_DAYS = 14   # within this many days after an occasion, suggest recovery actions
CLEARANCE_MAX_PCT = 8.0


def _units_on(sales: List[dict], product_id: str, day: date) -> Optional[int]:
    iso = day.isoformat()
    for s in sales:
        if s.get("product_id") == product_id and s.get("date") == iso:
            return int(s.get("units_sold") or 0)
    return None


def _review_block(short: str, event_days: List[date], products: List[dict], affected_ids: set,
                  sales: List[dict]) -> Optional[dict]:
    """Actual sales on the occasion vs a normal same weekday (average of the 4 weeks before)."""
    rows = []
    for p in products:
        actual, normal = 0, 0.0
        for d in event_days:
            a = _units_on(sales, p["product_id"], d)
            if a is None:
                continue
            prior = [_units_on(sales, p["product_id"], d - timedelta(days=7 * k)) for k in range(1, 5)]
            prior = [x for x in prior if x is not None]
            if not prior:
                continue
            actual += a
            normal += sum(prior) / len(prior)
        if normal > 0:
            rows.append((p, actual, normal, actual / normal))
    if not rows:
        return None
    rows.sort(key=lambda r: r[3], reverse=True)
    weekday = event_days[0].strftime("%A")
    lines = []
    for p, actual, normal, lift in rows[:5]:
        tag = "" if p["product_id"] in affected_ids or not affected_ids else " (not expected to be affected)"
        change = f"{lift:.1f}x normal" if lift >= 1.05 else ("about normal" if lift > 0.95 else f"{(1 - lift) * 100:.0f}% below normal")
        lines.append(f"{_short_name(p['name'])}: sold {actual} {p.get('unit', 'units')} vs about {normal:.0f} "
                     f"on a normal {weekday}: {change}{tag}.")
    days_txt = _fmt_day(event_days[0]) if len(event_days) == 1 else f"{_fmt_day(event_days[0])} to {_fmt_day(event_days[-1])}"
    return {"title": f"How {short} went ({days_txt})", "lines": lines}


def _expected_demand_block(affected: List[tuple], sales: List[dict], day: date, title: str) -> Optional[dict]:
    """Normal daily sales (last 28 days) x the occasion's multiplier, per affected product."""
    since = (date.today() - timedelta(days=27)).isoformat()
    lines = []
    for p, mult in sorted(affected, key=lambda x: x[1], reverse=True)[:5]:
        units = [int(s.get("units_sold") or 0) for s in sales
                 if s.get("product_id") == p["product_id"] and (s.get("date") or "") >= since]
        if not units:
            continue
        normal = sum(units) / 28.0
        lines.append(f"{_short_name(p['name'])}: about {normal:.0f}/day normally, so roughly {normal * mult:.0f} "
                     f"on the day ({mult:g}x), about {normal * (mult - 1):.0f} extra {p.get('unit', 'units')}.")
    if not lines:
        return None
    lines.append("Estimates from your last 4 weeks of sales and the calendar's demand multipliers.")
    return {"title": title, "lines": lines}


def _past_occasion_plan(plan, event, short, start, end, event_days, affected, merchant, products, sales,
                        partner_suggestions, next_occurrence) -> dict:
    today = date.today()
    days_since = (today - end).days
    ago = "yesterday" if days_since == 1 else f"{days_since} days ago"
    date_txt = _fmt_day(start) + (f" {start.year}" if start.year != today.year else "")
    affected_ids = {p["product_id"] for p, _ in affected}

    # 1. Review: actual sales on the day vs a normal same weekday
    review = _review_block(short, event_days, products, affected_ids, sales)
    if review:
        plan["insights"].append(review)
    else:
        first = min((s.get("date") for s in sales if s.get("date")), default=None)
        plan["notes"].append(
            f"There are no sales records for {_fmt_day(start)}"
            + (f" (records start on {first})" if first else "") + ", so there's nothing to review yet."
        )

    # 2. Recovery actions, only shortly after the occasion
    if days_since <= RECENT_PAST_DAYS:
        stock_cover = []
        for p in products:
            v = sum(int(s.get("units_sold") or 0) for s in sales if s.get("product_id") == p["product_id"]
                    and (s.get("date") or "") >= (today - timedelta(days=13)).isoformat()) / 14.0
            stock_cover.append((p, (int(p.get("current_stock") or 0) / v) if v > 0 else 99.0))
        covers = sorted(c for _, c in stock_cover if c < 99)
        typical = covers[len(covers) // 2] if covers else 0.0

        # a) Refill products the rush ran down (normal forecast, no festival boost)
        for p, _ in affected:
            stock, threshold = int(p.get("current_stock") or 0), int(p.get("reorder_threshold") or 10)
            if stock > threshold or len([d for d in plan["drafts"] if d["action_type"] == "RESTOCK_INVENTORY"]) >= 3:
                continue
            p_sales = [s for s in sales if s.get("product_id") == p["product_id"]]
            fc = forecasting_service.forecast_product(p, p_sales, horizon_days=14,
                                                      merchant_category=merchant.get("category"))
            qty = fc.total_forecasted_units + threshold - stock
            if qty <= 0:
                continue
            unit = p.get("unit", "units")
            plan["drafts"].append(DraftAction(
                action_type="RESTOCK_INVENTORY",
                title=f"Refill {p['name']} after {short}",
                description=(f"Stock is down to {stock} {unit} (reorder level {threshold}). Add {qty} {unit} "
                             f"to cover the next 2 weeks of normal demand plus your buffer."),
                payload={"product_id": p["product_id"], "product_name": p["name"], "quantity": int(qty),
                         "adjustment_type": "RESTOCK", "notes": f"Post-{short} refill"},
            ).model_dump())

        # b) Clear leftover stock that didn't sell (well above this shop's usual stock level)
        leftovers = [(p, c) for p, c in stock_cover
                     if p["product_id"] in affected_ids and typical > 0 and 1.5 * typical <= c < 99]
        for p, cover in sorted(leftovers, key=lambda x: x[1], reverse=True):
            disc = float(int(min(CLEARANCE_MAX_PCT, max_discount_above_cost(p) - OFFER_MARGIN_BUFFER)))
            if disc < 3 or check_discount_vs_cost(p, disc) is not None:
                continue
            plan["drafts"].append(DraftAction(
                action_type="CREATE_CAMPAIGN",
                title=f"Post-{short} clearance: {disc:g}% off {_short_name(p['name'])}",
                description=(f"{int(p.get('current_stock') or 0)} {p.get('unit', 'units')} left, about {cover:.0f} days of "
                             f"sales (your shop usually holds about {typical:.0f}). A {disc:g}% offer for a week "
                             f"clears it while staying above cost."),
                payload={"title": f"Post-{short} Clearance: {_short_name(p['name'])}", "campaign_type": "Special Discount",
                         "target_product_ids": [p["product_id"]], "discount_pct": disc, "budget_allocated": 800.0,
                         "start_date": today.isoformat(), "end_date": (today + timedelta(days=6)).isoformat(),
                         "target_redemptions_goal": 40},
            ).model_dump())
            break
        if not plan["drafts"]:
            plan["notes"].append("Stock levels look fine after the occasion: nothing to refill or clear.")

    # 3. The next time this occasion comes round
    if next_occurrence:
        try:
            nxt = date.fromisoformat(next_occurrence.get("start_date"))
        except (TypeError, ValueError):
            nxt = None
        if nxt and nxt > today:
            n_days = (nxt - today).days
            if n_days <= RESTOCK_WINDOW_DAYS:
                ahead = build_event_action_plan(next_occurrence, merchant, products, sales, partner_suggestions)
                plan["notes"].append(f"Next {short}: {_fmt_day(nxt)}, in {n_days} days. Prep actions are included below.")
                plan["drafts"].extend(ahead["drafts"])
                plan["ideas"].extend(ahead["ideas"])
            else:
                plan["notes"].append(f"Next {short}: {_fmt_day(nxt)} {nxt.year}, in {n_days} days. "
                                     f"Restock suggestions open about 3 weeks before.")
                block = _expected_demand_block(affected, sales, nxt, f"Expected demand next {short} ({_fmt_day(nxt)})")
                if block:
                    plan["insights"].append(block)
    elif not plan["insights"]:
        block = _expected_demand_block(affected, sales, start, f"If {short} comes round again")
        if block:
            plan["insights"].append(block)

    if not affected and not plan["insights"]:
        plan["notes"].append(f"{short} isn't expected to change demand for your products much.")

    # Headline that matches what the plan actually contains
    has_review = bool(review)
    has_actions = bool(plan["drafts"])
    tail = ("Here's how it went and what to do now." if has_review and has_actions
            else "Here's how it went." if has_review
            else "Here's what to do now." if has_actions
            else "Here's what to expect next time." if plan["insights"]
            else "")
    plan["headline"] = f"{short} was {ago} ({date_txt}). {tail}".strip()
    return plan
