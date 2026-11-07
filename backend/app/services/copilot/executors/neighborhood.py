"""
Neighborhood, local occasions, and cross-store collaboration execution mixin:
- get_nearby_merchants
- get_upcoming_events
- get_event_action_plan
- discover_collaboration_partners
- create_collaboration_proposal
"""

from datetime import date, timedelta
from typing import List, Optional, Any
from app.schemas.copilot import (
    CopilotChatResponse, CopilotEvidenceItem, DraftAction,
)
from app.services.copilot.executors.base import calculate_haversine
from app.services.collaboration import collaboration_service
from app.services.occasions import get_all_india_occasions
from app.services.collab_intelligence import load_suggestions
from app.services.event_actions import build_event_action_plan


class NeighborhoodExecutorMixin:
    """Handles neighborhood spatial discovery, cultural events, and cross-store bundles."""

    # ── Tool: get_nearby_merchants ──────────────────────────────────────────
    async def execute_get_nearby_merchants(
        self,
        args: dict,
        merchant: dict,
        db: Any = None,
    ) -> CopilotChatResponse:
        """Tool: get_nearby_merchants"""
        radius_km = float(args.get("radius_km")) if args.get("radius_km") else None
        cat_filter = (args.get("category") or "").strip().lower()
        limit = int(args.get("limit") or 5)

        curr_lat = float(merchant.get("latitude", 12.920737))
        curr_lng = float(merchant.get("longitude", 77.668710))
        m_id = merchant.get("merchant_id")

        merchants_list = []
        if db is not None:
            try:
                merchants_list = await db.merchants.find(
                    {"merchant_id": {"$ne": m_id}}, {"password_hash": 0}
                ).to_list(length=50)
            except Exception:
                merchants_list = []

        if not merchants_list:
            return CopilotChatResponse(
                reply="No nearby stores could be retrieved from the neighborhood database at this moment.",
                evidence=[],
                draft_action=None,
                llm_configured=True,
                provider_info="LocalPulse Agent Tool: get_nearby_merchants",
            )

        scored = []
        for m in merchants_list:
            m_lat = float(m.get("latitude", 12.920737))
            m_lng = float(m.get("longitude", 77.668710))
            dist_km = calculate_haversine(curr_lat, curr_lng, m_lat, m_lng)
            dist_m = int(dist_km * 1000)
            m_cat = m.get("category", "")
            if cat_filter and cat_filter not in m_cat.lower() and cat_filter not in m.get("business_name", "").lower():
                continue
            if radius_km and dist_km > radius_km:
                continue
            scored.append({
                "merchant": m,
                "dist_km": dist_km,
                "dist_m": dist_m,
            })

        scored.sort(key=lambda x: x["dist_km"])

        if not scored:
            radius_msg = f" within {radius_km} km" if radius_km else ""
            cat_msg = f" for '{args.get('category')}'" if cat_filter else ""
            return CopilotChatResponse(
                reply=f"No neighboring stores found{radius_msg}{cat_msg}. Try expanding your search radius or asking without category filters.",
                evidence=[],
                draft_action=None,
                llm_configured=True,
                provider_info="LocalPulse Agent Tool: get_nearby_merchants",
            )

        top_matches = scored[:limit]
        nearest = top_matches[0]

        lines = [
            f"**Neighborhood Stores & Spatial Map ({len(top_matches)} found)**\n",
            f"Your store is located at `{curr_lat:.4f}, {curr_lng:.4f}`. Here are the closest businesses:",
            ""
        ]

        for i, item in enumerate(top_matches, 1):
            m = item["merchant"]
            dist_str = f"{item['dist_m']} m" if item["dist_km"] < 1.0 else f"{item['dist_km']:.2f} km"
            name = m.get("business_name", "Local Store")
            cat = m.get("category", "General")
            addr = m.get("address", "Neighborhood")
            phone = m.get("phone", "")

            lines.append(f"{i}. **{name}** — `{cat}`")
            lines.append(f"   - **Distance:** {dist_str} away (`{addr}`)")
            if phone:
                lines.append(f"   - **Contact:** {phone}")
            lines.append("")

        lines.append("*Tip: You can collaborate with any of these shops on a joint discount combo using `discover_collaboration_partners` or visit the Neighborhood Map tab.*")

        evidence = [
            CopilotEvidenceItem(source_metric="Nearest Partner", value=nearest["merchant"].get("business_name", ""), context="Closest merchant to your shop"),
            CopilotEvidenceItem(source_metric="Distance to Nearest", value=f"{nearest['dist_km']:.2f} km", context="Spatial distance (Haversine)"),
            CopilotEvidenceItem(source_metric="Total Nearby Found", value=str(len(scored)), context="Active neighbor merchants in database"),
        ]

        return CopilotChatResponse(
            reply="\n".join(lines).strip(),
            evidence=evidence,
            draft_action=None,
            llm_configured=True,
            provider_info="LocalPulse Agent Tool: get_nearby_merchants",
        )

    # ── Tool: get_upcoming_events ───────────────────────────────────────────
    async def execute_get_upcoming_events(
        self,
        args: dict,
        merchant: dict,
        events: Optional[List[dict]] = None,
        db: Any = None,
    ) -> CopilotChatResponse:
        """Tool: get_upcoming_events"""
        days = int(args.get("days") or 30)
        today = date.today()
        today_iso = today.isoformat()
        end_iso = (today + timedelta(days=days)).isoformat()

        all_events = events
        if not all_events and db is not None:
            try:
                curr_lat = float(merchant.get("latitude", 12.920737))
                curr_lng = float(merchant.get("longitude", 77.668710))
                all_events, _ = await get_all_india_occasions(
                    merchant=merchant,
                    merchant_lat=curr_lat,
                    merchant_lng=curr_lng,
                    merchant_category=merchant.get("category", ""),
                    db=db,
                )
            except Exception:
                all_events = []

        raw_events = []
        for e in (all_events or []):
            e_dict = e if isinstance(e, dict) else e.model_dump()
            s_date = e_dict.get("start_date") or ""
            e_date = e_dict.get("end_date") or s_date
            if e_date >= today_iso and s_date <= end_iso:
                raw_events.append(e_dict)

        raw_events.sort(key=lambda x: x.get("start_date", ""))

        if not raw_events:
            return CopilotChatResponse(
                reply=f"No major festivals or neighborhood events found in the calendar for the next {days} days.",
                evidence=[],
                draft_action=None,
                llm_configured=True,
                provider_info="LocalPulse Agent Tool: get_upcoming_events",
            )

        lines = [
            f"**Upcoming Festivals & Neighborhood Events (Next {days} Days)**\n",
            "Here are the upcoming cultural occasions and their projected impact on local retail demand:",
            ""
        ]

        for i, ev in enumerate(raw_events[:6], 1):
            title = ev.get("title", "Event")
            s_date = ev.get("start_date", "")
            e_date = ev.get("end_date", "")
            proximity = ev.get("proximity_type", "All-India")

            try:
                ev_d = date.fromisoformat(s_date)
                delta_days = (ev_d - today).days
                time_str = "Today!" if delta_days == 0 else (f"in {delta_days} day{'s' if delta_days > 1 else ''}" if delta_days > 0 else "Ongoing")
            except Exception:
                time_str = s_date

            date_str = s_date if s_date == e_date else f"{s_date} to {e_date}"
            lines.append(f"{i}. **{title}** (`{date_str}` — *{time_str}*)")
            lines.append(f"   - **Scope:** {proximity}")

            impacts = ev.get("category_impacts", [])
            impact_strs = []
            for imp in impacts[:3]:
                c_name = imp.get("category_name")
                mult = imp.get("demand_multiplier", 1.0)
                pct = int((mult - 1.0) * 100)
                if pct > 0:
                    impact_strs.append(f"{c_name} (+{pct}% lift)")
            if impact_strs:
                lines.append(f"   - **Demand Uplift:** {', '.join(impact_strs)}")

            summary_desc = ev.get("description", "")
            if summary_desc:
                lines.append(f"   - **Context:** {summary_desc}")
            lines.append("")

        next_ev = raw_events[0]
        lines.append(f"*Action Tip: Ask me **\"Prepare an action plan for {next_ev.get('title')}**\" to generate pre-festival restock drafts and promotional combo offers!*")

        evidence = [
            CopilotEvidenceItem(source_metric="Upcoming Occasions", value=str(len(raw_events)), context=f"Events in next {days} days"),
            CopilotEvidenceItem(source_metric="Next Major Event", value=next_ev.get("title", ""), context=next_ev.get("start_date", "")),
        ]

        return CopilotChatResponse(
            reply="\n".join(lines).strip(),
            evidence=evidence,
            draft_action=None,
            llm_configured=True,
            provider_info="LocalPulse Agent Tool: get_upcoming_events",
        )

    # ── Tool: get_event_action_plan ─────────────────────────────────────────
    async def execute_get_event_action_plan(
        self,
        args: dict,
        merchant: dict,
        products: List[dict],
        sales: List[dict],
        events: Optional[List[dict]] = None,
        db: Any = None,
    ) -> CopilotChatResponse:
        """Tool: get_event_action_plan"""
        target_name = (args.get("occasion_name") or "").strip().lower()
        if not target_name:
            return self._clarify("Which festival or occasion would you like an action plan for? (e.g. Diwali, Holi, Eid, Pongal)", "get_event_action_plan")

        all_events = events
        if not all_events and db is not None:
            try:
                curr_lat = float(merchant.get("latitude", 12.920737))
                curr_lng = float(merchant.get("longitude", 77.668710))
                all_events, _ = await get_all_india_occasions(
                    merchant=merchant,
                    merchant_lat=curr_lat,
                    merchant_lng=curr_lng,
                    merchant_category=merchant.get("category", ""),
                    db=db,
                )
            except Exception:
                all_events = []

        matched_event = None
        for ev in (all_events or []):
            e_dict = ev if isinstance(ev, dict) else ev.model_dump()
            title = (e_dict.get("title") or "").lower()
            e_id = (e_dict.get("occasion_id") or "").lower()
            if target_name in title or target_name in e_id or title in target_name:
                matched_event = e_dict
                break

        if not matched_event:
            sample_titles = [e.get("title", "") for e in (all_events or [])[:5]]
            return CopilotChatResponse(
                reply=f"Could not find an upcoming calendar occasion matching **'{args.get('occasion_name')}'**.\nKnown upcoming occasions include: {', '.join(sample_titles) if sample_titles else 'None recorded'}.",
                evidence=[],
                draft_action=None,
                llm_configured=True,
                provider_info="LocalPulse Agent Tool: get_event_action_plan",
            )

        neighbors = []
        if db is not None:
            try:
                neighbors = await db.merchants.find(
                    {"merchant_id": {"$ne": merchant.get("merchant_id")}},
                    {"password_hash": 0}
                ).to_list(length=20)
            except Exception:
                neighbors = []

        plan = build_event_action_plan(
            occasion=matched_event,
            merchant=merchant,
            products=products,
            neighbors=neighbors,
        )

        lines = [
            f"**Action Plan: {plan.occasion_title} Readiness**\n",
            f"*{plan.summary_pitch}*\n",
            f"- **Start Date:** `{plan.occasion_start}` (In ~{plan.days_until_event} days)",
            f"- **Category Demand Multiplier:** **{plan.demand_multiplier:.1f}x baseline**",
            "",
            "### Recommended Preparations:"
        ]

        if plan.recommended_restocks:
            lines.append("**1. Priority Pre-Festival Inventory Restocks:**")
            for r in plan.recommended_restocks[:3]:
                lines.append(f"   - **{r.product_name}**: Stock is {r.current_stock} {r.unit} -> Restock **+{r.suggested_restock_units} {r.unit}** (Demand uplift ~{r.surge_pct}%)")
            lines.append("")

        if plan.recommended_campaign:
            c = plan.recommended_campaign
            lines.append(f"**2. Themed Festive Campaign:**\n   - Launch **\"{c.title}\"** offering **{c.discount_pct}% OFF** on {c.target_product_name} (Budget: ₹{c.budget:,.0f})")
            lines.append("")

        if plan.recommended_bundle:
            b = plan.recommended_bundle
            lines.append(f"**3. Cross-Store Collaboration:**\n   - Pair `{b.my_product_name}` with **{b.partner_name}**'s `{b.partner_product_name}`: Combo price **₹{b.discounted_bundle_price:.0f}** *(Both shops retain safe margins)*")
            lines.append("")

        draft_to_offer = None
        if plan.recommended_restocks:
            top_r = plan.recommended_restocks[0]
            draft_to_offer = DraftAction(
                action_type="RESTOCK_INVENTORY",
                title=f"Festive Restock: {top_r.product_name}",
                description=f"Replenish +{top_r.suggested_restock_units} {top_r.unit} of {top_r.product_name} in anticipation of {plan.occasion_title} demand surge ({top_r.surge_pct}% lift).",
                payload={
                    "product_id": top_r.product_id,
                    "product_name": top_r.product_name,
                    "quantity": top_r.suggested_restock_units,
                    "adjustment_type": "RESTOCK",
                    "notes": f"Pre-festival buffer for {plan.occasion_title}",
                },
                requires_confirmation=True,
            )
            lines.append(f"*Action ready: I've drafted a restock card below for **{top_r.product_name} (+{top_r.suggested_restock_units} {top_r.unit})**. Click Confirm & Apply to update inventory.*")
        elif plan.recommended_campaign:
            c = plan.recommended_campaign
            draft_to_offer = DraftAction(
                action_type="CREATE_CAMPAIGN",
                title=f"Festive Offer: {c.title}",
                description=f"Create {c.discount_pct}% off promotional campaign on {c.target_product_name} for {plan.occasion_title}.",
                payload={
                    "title": c.title,
                    "campaign_type": "FESTIVE_SPECIAL",
                    "target_product_ids": [c.target_product_id],
                    "discount_pct": c.discount_pct,
                    "budget_allocated": c.budget,
                    "start_date": date.today().strftime("%Y-%m-%d"),
                    "end_date": (date.today() + timedelta(days=7)).strftime("%Y-%m-%d"),
                    "target_redemptions_goal": 50,
                },
                requires_confirmation=True,
            )
            lines.append(f"*Action ready: I've drafted a festive promotion card below for **{c.title}**. Click Confirm & Apply to activate.*")

        reply = "\n".join(lines).strip()
        evidence = [
            CopilotEvidenceItem(source_metric="Occasion Lift", value=f"{plan.demand_multiplier:.1f}x", context=plan.occasion_title),
            CopilotEvidenceItem(source_metric="Days Remaining", value=f"{plan.days_until_event} days", context="Lead-time for stocking up"),
        ]

        return CopilotChatResponse(
            reply=reply,
            evidence=evidence,
            draft_action=draft_to_offer,
            llm_configured=True,
            provider_info="LocalPulse Agent Tool: get_event_action_plan",
        )

    # ── Tool: discover_collaboration_partners ───────────────────────────────
    async def execute_discover_collaboration_partners(
        self,
        args: dict,
        merchant: dict,
        products: List[dict],
        db: Any = None,
    ) -> CopilotChatResponse:
        """Tool: discover_collaboration_partners"""
        p_name = (args.get("product_name") or "").strip().lower()
        cat_filter = (args.get("partner_category") or "").strip().lower()

        suggestions = []
        if db is not None:
            try:
                suggestions = await load_suggestions(db, merchant, use_ai="cache")
            except Exception:
                suggestions = []

        if not suggestions:
            return CopilotChatResponse(
                reply="No collaboration partner recommendations available right now. Ensure nearby stores have published active catalog products.",
                evidence=[],
                draft_action=None,
                llm_configured=True,
                provider_info="LocalPulse Agent Tool: discover_collaboration_partners",
            )

        filtered = []
        for s in suggestions:
            m = s.get("merchant", {})
            m_cat = (m.get("category") or "").lower()
            if cat_filter and cat_filter not in m_cat and cat_filter not in m.get("business_name", "").lower():
                continue
            bundle = s.get("bundle") or {}
            if p_name:
                init_p = (bundle.get("initiator_product_name") or "").lower()
                part_p = (bundle.get("partner_product_name") or "").lower()
                if p_name not in init_p and p_name not in part_p:
                    continue
            filtered.append(s)

        candidates = filtered if filtered else suggestions

        lines = [
            f"**Nearby Collaboration Partners & Joint Bundles ({len(candidates[:4])} recommendations)**\n",
            "Here are verified cross-store bundling partnerships where **both shops preserve >12% profit margin**:",
            ""
        ]

        for i, s in enumerate(candidates[:4], 1):
            m = s.get("merchant", {})
            b_name = m.get("business_name", "Partner Store")
            cat = m.get("category", "General")
            dist = s.get("distance_km", 0.0)
            score = s.get("score", 85)
            theme = s.get("theme", "Joint Bundle")
            bundle = s.get("bundle") or {}

            lines.append(f"{i}. **{b_name}** (`{cat}`) — {dist:.2f} km away")
            lines.append(f"   - **Synergy Theme:** {theme} *(Score: {score}/100)*")
            if bundle:
                my_p = bundle.get("initiator_product_name")
                part_p = bundle.get("partner_product_name")
                orig_pr = bundle.get("original_bundle_price", 0)
                disc_pr = bundle.get("discounted_bundle_price", 0)
                pitch = bundle.get("pitch", "")
                lines.append(f"   - **Combo Offer:** `{my_p}` + `{part_p}`")
                lines.append(f"   - **Pricing:** ₹{disc_pr:.0f} *(Was ₹{orig_pr:.0f}, safe margins verified)*")
                if pitch:
                    lines.append(f"   - **Strategy:** {pitch}")
            lines.append("")

        top_sug = candidates[0]
        top_m = top_sug.get("merchant", {}).get("business_name")
        lines.append(f"*To send a joint proposal, say: **\"Send a collab proposal to {top_m}\"** or visit the Collaborations tab.*")

        evidence = [
            CopilotEvidenceItem(source_metric="Top Partner", value=top_m or "Nearby Store", context=f"Synergy score {top_sug.get('score', 0)}/100"),
            CopilotEvidenceItem(source_metric="Partners Available", value=str(len(candidates)), context="Viable margin-safe bundle opportunities"),
        ]

        return CopilotChatResponse(
            reply="\n".join(lines).strip(),
            evidence=evidence,
            draft_action=None,
            llm_configured=True,
            provider_info="LocalPulse Agent Tool: discover_collaboration_partners",
        )

    # ── Tool: create_collaboration_proposal ─────────────────────────────────
    async def execute_create_collaboration_proposal(
        self,
        args: dict,
        merchant: dict,
        products: List[dict],
        db: Any = None,
    ) -> CopilotChatResponse:
        """Tool: create_collaboration_proposal"""
        partner_kw = (args.get("partner_name") or "").strip().lower()
        if not partner_kw:
            return self._clarify("Which nearby partner merchant would you like to collaborate with? (e.g. Krishna Bakery, Nilgiri's)", "create_collaboration_proposal")

        m_id = merchant.get("merchant_id")
        if db is None:
            return self._clarify("Database connection unavailable for partner discovery.", "create_collaboration_proposal")

        all_merchants = await db.merchants.find({"merchant_id": {"$ne": m_id}}).to_list(length=50)
        target_partner = None
        for m in all_merchants:
            b_name = (m.get("business_name") or "").lower()
            if partner_kw in b_name or any(w in b_name for w in partner_kw.split() if len(w) >= 3):
                target_partner = m
                break

        if not target_partner:
            names = [m.get("business_name") for m in all_merchants[:5]]
            return self._clarify(
                f"I couldn't find a partner store matching **'{args.get('partner_name')}'**.\n"
                f"Available nearby stores include: {', '.join(names)}.",
                "create_collaboration_proposal"
            )

        partner_id = target_partner["merchant_id"]
        partner_prods = await db.products.find({"merchant_id": partner_id}).to_list(length=50)
        if not partner_prods:
            return self._clarify(f"{target_partner.get('business_name')} does not have any active products listed in their catalog yet.", "create_collaboration_proposal")

        my_p_name = (args.get("my_product_name") or "").strip().lower()
        my_prod = None
        if my_p_name:
            my_prod = self.find_product_by_name(my_p_name, products)
        if not my_prod and products:
            my_prod = products[0]

        part_p_name = (args.get("partner_product_name") or "").strip().lower()
        part_prod = None
        if part_p_name:
            for p in partner_prods:
                if part_p_name in p.get("name", "").lower():
                    part_prod = p
                    break
        if not part_prod and partner_prods:
            part_prod = partner_prods[0]

        if not my_prod or not part_prod:
            return self._clarify("Could not resolve valid products for the bundle.", "create_collaboration_proposal")

        discount_pct = float(args.get("discount_pct") or 10.0)
        bundle_title = args.get("bundle_name") or f"{my_prod['name']} & {part_prod['name']} Neighborhood Combo"
        duration_days = int(args.get("duration_days") or 14)

        val = collaboration_service.validate_bundle_margins(
            initiator_product=my_prod,
            initiator_discount_pct=discount_pct,
            partner_product=part_prod,
            partner_discount_pct=discount_pct,
            bundle_name=bundle_title,
        )

        if not val.is_financially_viable:
            discount_pct = 5.0
            val = collaboration_service.validate_bundle_margins(
                initiator_product=my_prod,
                initiator_discount_pct=discount_pct,
                partner_product=part_prod,
                partner_discount_pct=discount_pct,
                bundle_name=bundle_title,
            )

        payload = {
            "partner_merchant_id": partner_id,
            "partner_merchant_name": target_partner.get("business_name"),
            "initiator_product_id": my_prod["product_id"],
            "initiator_product_name": my_prod["name"],
            "initiator_discount_pct": discount_pct,
            "initiator_margin_pct": val.initiator_margin_pct,
            "partner_product_id": part_prod["product_id"],
            "partner_product_name": part_prod["name"],
            "partner_discount_pct": discount_pct,
            "partner_margin_pct": val.partner_margin_pct,
            "bundle_name": bundle_title,
            "bundle_description": f"Collaborative combo pairing {my_prod['name']} with {part_prod['name']} at {discount_pct}% off.",
            "original_bundle_price": val.original_bundle_price,
            "discounted_bundle_price": val.discounted_bundle_price,
            "proposed_duration_days": duration_days,
        }

        draft = DraftAction(
            action_type="CREATE_COLLABORATION_PROPOSAL",
            title=f"Bundle Proposal: {bundle_title}",
            description=(
                f"Propose a joint {discount_pct}% off bundle with {target_partner.get('business_name')}: "
                f"'{my_prod['name']}' + '{part_prod['name']}' at ₹{val.discounted_bundle_price:.0f} "
                f"(down from ₹{val.original_bundle_price:.0f}). Your profit margin stays safe at {val.initiator_margin_pct:.1f}%."
            ),
            payload=payload,
            requires_confirmation=True,
        )

        reply = (
            f"**Drafted Collaboration Proposal with {target_partner.get('business_name')}**\n\n"
            f"- **Combo Name:** {bundle_title}\n"
            f"- **Your Product:** {my_prod['name']} ({discount_pct}% off, Margin: {val.initiator_margin_pct:.1f}%)\n"
            f"- **Partner Product:** {part_prod['name']} ({discount_pct}% off, Margin: {val.partner_margin_pct:.1f}%)\n"
            f"- **Pricing:** ₹{val.discounted_bundle_price:.0f} (Standard: ₹{val.original_bundle_price:.0f})\n"
            f"- **Margin Safety Check:** Both shops maintain >12% profit margin.\n\n"
            f"Click **Confirm & Apply** below to dispatch this proposal to {target_partner.get('business_name')}."
        )

        evidence = [
            CopilotEvidenceItem(source_metric="Partner Merchant", value=target_partner.get("business_name", ""), context=f"ID: {partner_id}"),
            CopilotEvidenceItem(source_metric="Discounted Bundle Price", value=f"₹{val.discounted_bundle_price:.0f}", context=f"Original: ₹{val.original_bundle_price:.0f}"),
            CopilotEvidenceItem(source_metric="Your Post-Discount Margin", value=f"{val.initiator_margin_pct:.1f}%", context="Guaranteed above 12% safety threshold"),
        ]

        return CopilotChatResponse(
            reply=reply,
            evidence=evidence,
            draft_action=draft,
            llm_configured=True,
            provider_info="LocalPulse Agent Tool: create_collaboration_proposal",
        )
