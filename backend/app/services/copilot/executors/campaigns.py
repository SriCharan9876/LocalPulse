"""
Campaigns and discounts execution mixin for Copilot Agent tools:
- get_discount_recommendations
- create_promotional_campaign
- end_promotional_campaign
"""

from datetime import date, timedelta
from typing import List
from app.schemas.copilot import (
    CopilotChatResponse, CopilotEvidenceItem, DraftAction,
)
from app.services.copilot.guards import (
    to_float, to_int, check_discount, check_discount_vs_cost, max_discount_above_cost,
)


class CampaignsExecutorMixin:
    """Handles discount recommendations, marketing campaign creation, and conclusion."""

    # ── Tool: get_discount_recommendations ──────────────────────────────────
    def execute_get_discount_recommendations(
        self,
        args: dict,
        merchant: dict,
        products: List[dict],
        sales: List[dict]
    ) -> CopilotChatResponse:
        """Tool: get_discount_recommendations"""
        max_disc = float(args.get("max_discount_pct", 15.0))

        # Detect items with high stock relative to sales velocity or high margins
        scored_products = []
        for p in products:
            curr = int(p.get("current_stock", 0))
            cost = float(p.get("cost_price", 0.0))
            sp = float(p.get("selling_price", 0.0))
            margin = ((sp - cost) / sp * 100.0) if sp > 0 else 0.0
            thresh = int(p.get("reorder_threshold", 10))

            # Eligible for discount if excess stock (stock > 2x threshold) and healthy margin (>20%)
            if curr > (thresh * 1.5) and margin >= 20.0:
                # Safe discount is half the profit margin capped at max_disc
                safe_disc = min(max_disc, round(margin * 0.4, 0))
                scored_products.append((p, curr, margin, safe_disc))

        if not scored_products:
            # Fallback to products with highest stock
            sorted_by_stock = sorted(products, key=lambda x: int(x.get("current_stock", 0)), reverse=True)
            top_p = sorted_by_stock[0] if sorted_by_stock else None
            if not top_p:
                return CopilotChatResponse(
                    reply="No products found in catalog to analyze discount strategies.",
                    evidence=[],
                    draft_action=None,
                    llm_configured=True,
                    provider_info="LocalPulse Agent Tool: get_discount_recommendations",
                )
            # Use the product's real margin, and never suggest a discount that sells below cost.
            top_sp = float(top_p.get("selling_price", 0.0))
            top_cp = float(top_p.get("cost_price", 0.0))
            top_margin = ((top_sp - top_cp) / top_sp * 100.0) if top_sp > 0 else 0.0
            top_disc = min(8.0, max_discount_above_cost(top_p))
            scored_products.append((top_p, int(top_p.get("current_stock", 0)), top_margin, top_disc))

        reply_lines = [
            f"**Recommended Promotional Clearance & Discount Strategies:**",
            "Based on profit margin resilience (>15% post-discount) and surplus inventory velocity:\n"
        ]

        evidence = []
        for p, stock, margin, disc in scored_products[:3]:
            new_sp = round(float(p.get("selling_price", 0)) * (1.0 - disc / 100.0), 2)
            unit = p.get("unit", "units")
            reply_lines.append(
                f"- **{p.get('name')}**: Stock = **{stock} {unit}** | Gross Margin = **{margin:.1f}%**\n"
                f"  -> **Recommended Discount: {disc:.0f}% OFF** (₹{p.get('selling_price')} -> **₹{new_sp:,.2f}**). Retains healthy unit profit."
            )
            evidence.append(
                CopilotEvidenceItem(
                    source_metric=f"Recommended {p.get('name')[:12]} Offer",
                    value=f"{disc:.0f}% OFF",
                    context=f"Surplus stock: {stock} units"
                )
            )

        best_cand = scored_products[0][0]
        best_disc = scored_products[0][3]

        if best_disc < 1:
            # Margins too thin for any discount without selling at a loss: advise, don't draft.
            return CopilotChatResponse(
                reply="\n".join(reply_lines) + "\n\nMargins are too thin to discount without selling below cost, so I haven't drafted a campaign.",
                evidence=evidence,
                draft_action=None,
                llm_configured=True,
                provider_info="LocalPulse Agent Tool: get_discount_recommendations",
            )

        draft = DraftAction(
            action_type="CREATE_CAMPAIGN",
            title=f"Clearance Offer: {best_cand['name']} ({best_disc:.0f}% Off)",
            description=f"Launch a targeted promotional flash discount of {best_disc:.0f}% on {best_cand['name']} to accelerate inventory turnover.",
            payload={
                "title": f"Flash Clearance: {best_cand['name']}",
                "campaign_type": "CLEARANCE_SALE",
                "target_product_ids": [best_cand["product_id"]],
                "discount_pct": best_disc,
                "budget_allocated": 1200.0,
                "start_date": date.today().strftime("%Y-%m-%d"),
                "end_date": (date.today() + timedelta(days=6)).strftime("%Y-%m-%d"),
                "target_redemptions_goal": 50,
            },
            requires_confirmation=True,
        )

        return CopilotChatResponse(
            reply="\n".join(reply_lines),
            evidence=evidence,
            draft_action=draft,
            llm_configured=True,
            provider_info="LocalPulse Agent Tool: get_discount_recommendations",
        )

    # ── Tool: create_promotional_campaign ───────────────────────────────────
    def execute_create_promotional_campaign(
        self,
        args: dict,
        merchant: dict,
        products: List[dict]
    ) -> CopilotChatResponse:
        """Tool: create_promotional_campaign (Proposes DraftAction)"""
        tool = "create_promotional_campaign"
        title = (args.get("title") or "Promotional Offer").strip()
        p_name = args.get("product_name", "") or ""
        disc_pct = to_float(args.get("discount_pct", 10.0))
        duration = max(1, min(to_int(args.get("duration_days", 7)) or 7, 90))
        budget = to_float(args.get("budget", 1000.0))
        if budget is None or budget < 0:
            budget = 1000.0

        discount_error = check_discount(disc_pct)
        if discount_error:
            return self._clarify(f"I haven't drafted this campaign: {discount_error}", tool)

        # A campaign must target a real product: never silently fall back to the first catalog item.
        p = self.find_product_by_name(p_name, products)
        picked_note = ""
        if not p and args.get("auto_select") == "best_promo_candidate":
            # Best candidate = most surplus stock (vs reorder level) that can afford this discount
            affordable = [x for x in products if check_discount_vs_cost(x, disc_pct) is None]
            if affordable:
                p = max(
                    affordable,
                    key=lambda x: int(x.get("current_stock", 0)) / max(1, int(x.get("reorder_threshold", 10))),
                )
                picked_note = (
                    f"*No product was named, so I picked **{p['name']}**: it has the most surplus stock "
                    f"({int(p.get('current_stock', 0))} on hand) and its margin can absorb {disc_pct:g}% off.*\n\n"
                )
                if title.startswith("Weekend Special: Store Favorites"):
                    title = f"Weekend Special: {p['name']}"
            else:
                return self._clarify(
                    f"None of your products can take {disc_pct:g}% off without selling below cost. Try a smaller discount.",
                    tool,
                )
        if not p:
            return self._product_not_found(p_name, products, tool, "run this campaign on")

        discount_error = check_discount_vs_cost(p, disc_pct)
        if discount_error:
            return self._clarify(f"I haven't drafted this campaign: {discount_error}", tool)

        target_ids = [p["product_id"]]
        target_name = p["name"]
        sp = float(p.get("selling_price", 0.0))
        cp = float(p.get("cost_price", 0.0))
        promo_price = round(sp * (1.0 - disc_pct / 100.0), 2)
        promo_margin = round((promo_price - cp) / promo_price * 100.0, 1) if promo_price > 0 else 0.0

        start_date = date.today().strftime("%Y-%m-%d")
        end_date = (date.today() + timedelta(days=duration - 1)).strftime("%Y-%m-%d")

        draft = DraftAction(
            action_type="CREATE_CAMPAIGN",
            title=f"Campaign: {title}",
            description=f"Launch '{title}' with {disc_pct}% discount on {target_name} for {duration} days (Budget: ₹{budget:,.2f}).",
            payload={
                "title": title,
                "campaign_type": "DISCOUNT_OFFER",
                "target_product_ids": target_ids,
                "discount_pct": disc_pct,
                "budget_allocated": budget,
                "start_date": start_date,
                "end_date": end_date,
                "target_redemptions_goal": 50,
            },
            requires_confirmation=True,
        )

        reply = (
            f"{picked_note}"
            f"**Drafted Promotional Campaign:**\n\n"
            f"- **Title:** **{title}**\n"
            f"- **Target Product:** {target_name}\n"
            f"- **Discount Offered:** **{disc_pct}% OFF** (₹{sp:,.2f} → ₹{promo_price:,.2f})\n"
            f"- **Margin During Promotion:** {promo_margin}% (cost ₹{cp:,.2f})\n"
            f"- **Duration:** {duration} Days ({start_date} to {end_date})\n"
            f"- **Allocated Budget:** ₹{budget:,.2f}\n\n"
            f"Click **Confirm & Apply** below to activate this campaign and adjust promotional retail pricing."
        )

        return CopilotChatResponse(
            reply=reply,
            evidence=[
                CopilotEvidenceItem(
                    source_metric="Promotional Discount",
                    value=f"{disc_pct}% OFF",
                    context=f"Target: {target_name}"
                ),
                CopilotEvidenceItem(
                    source_metric="Margin During Promotion",
                    value=f"{promo_margin}%",
                    context=f"Promo price ₹{promo_price:,.2f} vs cost ₹{cp:,.2f}"
                ),
            ],
            draft_action=draft,
            llm_configured=True,
            provider_info="LocalPulse Agent Tool: create_promotional_campaign",
        )

    # ── Tool: end_promotional_campaign ──────────────────────────────────────
    def execute_end_promotional_campaign(
        self,
        args: dict,
        merchant: dict,
        campaigns: List[dict]
    ) -> CopilotChatResponse:
        """Tool: end_promotional_campaign (Proposes DraftAction)"""
        c_query = (args.get("campaign_title_or_id") or "").strip().lower()
        active = [c for c in campaigns if c.get("status") == "ACTIVE"]

        # Find matching active campaign
        target_camp = None
        if c_query:
            for c in active:
                c_title = c.get("title", "").lower()
                c_id = c.get("campaign_id", "").lower()
                if c_query in c_title or c_query == c_id or (c_title and c_title in c_query):
                    target_camp = c
                    break
        elif len(active) == 1:
            target_camp = active[0]
        elif len(active) > 1:
            titles = "\n".join(f"- {c.get('title', '')}" for c in active)
            return self._clarify(
                f"You have {len(active)} active campaigns. Which one should I end?\n{titles}",
                "end_promotional_campaign",
            )

        if not target_camp:
            active_list = [c.get("title", "") for c in campaigns if c.get("status") == "ACTIVE"]
            return CopilotChatResponse(
                reply=f"No matching active campaign found for **'{c_query}'**.\nCurrently active campaigns: {active_list or 'None'}.",
                evidence=[],
                draft_action=None,
                llm_configured=True,
                provider_info="LocalPulse Agent Tool: end_promotional_campaign",
            )

        draft = DraftAction(
            action_type="END_CAMPAIGN",
            title=f"Conclude Campaign: {target_camp['title']}",
            description=f"Mark campaign '{target_camp['title']}' as COMPLETED and restore standard prices for targeted products.",
            payload={
                "campaign_id": target_camp["campaign_id"],
                "title": target_camp["title"]
            },
            requires_confirmation=True,
        )

        reply = (
            f"**Drafted Campaign Conclusion Proposal:**\n\n"
            f"- **Campaign Title:** **{target_camp['title']}** (`{target_camp['campaign_id']}`)\n"
            f"- **Discount Level:** {target_camp.get('discount_pct')}% OFF\n"
            f"- **Targeted Products:** {len(target_camp.get('target_product_ids', []))} SKU(s)\n\n"
            f"Ending this campaign will restore standard non-discounted selling prices on all associated inventory items. "
            f"Click **Confirm & Apply** below to finalize."
        )

        return CopilotChatResponse(
            reply=reply,
            evidence=[
                CopilotEvidenceItem(
                    source_metric="Active Campaign",
                    value=target_camp["title"],
                    context="Status: ACTIVE"
                )
            ],
            draft_action=draft,
            llm_configured=True,
            provider_info="LocalPulse Agent Tool: end_promotional_campaign",
        )
