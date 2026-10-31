"""
Execution handlers for Copilot Agent tools.
Separates read-only analytical executions from draft mutation proposals.
"""

import re
import uuid
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional, Tuple
from app.schemas.copilot import (
    CopilotChatResponse, CopilotEvidenceItem, DraftAction,
    ActionConfirmationResponse, ChartData, ChartPoint,
)
from app.services.forecasting import forecasting_service
from app.services.time_periods import Period, period_from_args, last_n_days
from app.services.action_guards import (
    to_float, to_int, normalize_adjustment_type, check_quantity,
    check_discount, check_discount_vs_cost, check_new_product,
    max_discount_above_cost,
)


class CopilotToolExecutor:
    """Executes read-only operations immediately and structures mutation drafts."""

    def _clarify(self, message: str, tool_name: str) -> CopilotChatResponse:
        """Reply without a draft action when the request can't be acted on as-is."""
        return CopilotChatResponse(
            reply=message,
            evidence=[],
            draft_action=None,
            llm_configured=True,
            provider_info=f"LocalPulse Agent Tool: {tool_name}",
        )

    def _product_not_found(self, p_name: str, products: List[dict], tool_name: str, verb: str) -> CopilotChatResponse:
        """Ask which product instead of guessing one."""
        available = ", ".join(p.get("name", "") for p in products[:6]) or "no products yet"
        if not (p_name or "").strip():
            msg = f"Which product would you like to {verb}?\nYour catalog includes: {available}."
        else:
            msg = (
                f"I couldn't find a product matching **'{p_name}'** in your catalog, so I haven't drafted anything.\n"
                f"Your catalog includes: {available}."
            )
        return self._clarify(msg, tool_name)

    def find_product_by_name(self, name_query: str, products: List[dict]) -> Optional[dict]:
        """Fuzzy match product by keyword or ID."""
        if not name_query or not products:
            return None
        q = name_query.strip().lower()
        # Direct exact or substring match
        for p in products:
            p_name = p.get("name", "").lower()
            p_id = p.get("product_id", "").lower()
            if q == p_name or q == p_id or q in p_name:
                return p
        # Token overlap match
        tokens = set(re.findall(r'\w+', q))
        best_match = None
        max_overlap = 0
        for p in products:
            p_tokens = set(re.findall(r'\w+', p.get("name", "").lower()))
            overlap = len(tokens.intersection(p_tokens))
            if overlap > max_overlap:
                max_overlap = overlap
                best_match = p
        return best_match if max_overlap > 0 else None

    def execute_analyze_product(
        self,
        args: dict,
        merchant: dict,
        products: List[dict],
        sales: List[dict],
        events: Optional[List[dict]] = None,
    ) -> CopilotChatResponse:
        """Tool: analyze_product_performance"""
        p_name = args.get("product_name", "") or ""
        period = period_from_args(args, default_days=7)
        target_p = self.find_product_by_name(p_name, products)
        picked_note = ""

        # "Analyze our top product" -> pick the best seller by revenue in the period
        if not target_p and args.get("auto_select") == "top_seller":
            ranked = self._rank_products(products, sales, period, rank_by="revenue")
            if ranked and ranked[0][1]["revenue"] > 0:
                target_p = ranked[0][0]
                picked_note = (
                    f"*Your top product by revenue for {period.label.lower()} is "
                    f"**{target_p['name']}**, so I analyzed that one.*\n\n"
                )

        if not target_p:
            return self._product_not_found(p_name, products, "analyze_product_performance", "analyze")

        p_id = target_p["product_id"]
        days = period.days
        # Filter sales for this product, then keep only the requested date range
        p_sales = [s for s in sales if s.get("product_id") == p_id]
        window_sales = [s for s in p_sales if period.contains(s.get("date", ""))]

        total_units = sum(int(s.get("units_sold", 0)) for s in window_sales)
        total_rev = sum(float(s.get("revenue", 0.0)) for s in window_sales)
        days_count = days  # calendar days (days with no sales count as zero)
        avg_daily_units = round(total_units / days_count, 1)

        curr_stock = int(target_p.get("current_stock", 0))
        runway_days = round(curr_stock / avg_daily_units, 1) if avg_daily_units > 0 else 99

        # Run forecasting model
        fc = forecasting_service.forecast_product(
            target_p, p_sales, horizon_days=7,
            events=events, merchant_category=merchant.get("category"),
        )

        evidence = [
            CopilotEvidenceItem(
                source_metric=f"Units Sold ({period.label})",
                value=f"{total_units} {target_p.get('unit', 'units')}",
                context=f"Average ~{avg_daily_units}/day over {days_count} day(s), {period.range_text()}"
            ),
            CopilotEvidenceItem(
                source_metric=f"Revenue ({period.label})",
                value=f"₹{total_rev:,.2f}",
                context=f"Current price ₹{float(target_p.get('effective_selling_price', target_p.get('selling_price', 0))):,.2f}"
            ),
            CopilotEvidenceItem(
                source_metric="Inventory Runway",
                value=f"~{runway_days} days",
                context=f"Current Stock: {curr_stock} {target_p.get('unit', 'units')}"
            )
        ]

        stock_warning = ""
        if fc.stockout_risk or curr_stock <= int(target_p.get("reorder_threshold", 10)):
            stock_warning = (
                f"\n\n**Stockout Warning:** Current stock ({curr_stock}) is below safety limits. "
                f"Projected 7-day demand is **{fc.total_forecasted_units} units**. "
                f"Recommended replenishment: **+{fc.recommended_replenishment_units} units**."
            )

        reply = (
            f"{picked_note}"
            f"**Performance Analysis for '{target_p['name']}' ({period.label}, {period.range_text()}):**\n\n"
            f"- **Category:** {target_p.get('category', 'General')}\n"
            f"- **Selling Price:** ₹{float(target_p.get('selling_price', 0)):,.2f} "
            f"(Effective: ₹{float(target_p.get('effective_selling_price', target_p.get('selling_price', 0))):,.2f})\n"
            f"- **Volume Sold ({period.label}):** **{total_units} {target_p.get('unit', 'units')}**\n"
            f"- **Total Revenue Generated:** **₹{total_rev:,.2f}**\n"
            f"- **Daily Average Velocity:** **{avg_daily_units} units/day**\n"
            f"- **Current Stock on Hand:** **{curr_stock} {target_p.get('unit', 'units')}** (~{runway_days} days of inventory runway)\n"
            f"- **Projected 7-Day Demand:** **{fc.total_forecasted_units} units** (Est. ₹{fc.total_projected_revenue:,.2f})"
            f"{stock_warning}"
        )

        draft = None
        if fc.stockout_risk and fc.recommended_replenishment_units > 0:
            draft = DraftAction(
                action_type="RESTOCK_INVENTORY",
                title=f"Restock {target_p['name']}",
                description=f"Replenish +{fc.recommended_replenishment_units} units to cover the next 2 weeks of projected demand plus a safety buffer.",
                payload={
                    "product_id": target_p["product_id"],
                    "product_name": target_p["name"],
                    "quantity": fc.recommended_replenishment_units,
                    "adjustment_type": "RESTOCK",
                    "notes": f"Triggered from {period.label.lower()} velocity analysis ({fc.total_forecasted_units} units projected)",
                },
                requires_confirmation=True,
            )

        return CopilotChatResponse(
            reply=reply,
            evidence=evidence,
            draft_action=draft,
            llm_configured=True,
            provider_info="LocalPulse Agent Tool: analyze_product_performance",
        )

    def execute_get_restock_recommendations(
        self,
        args: dict,
        merchant: dict,
        products: List[dict],
        sales: List[dict]
    ) -> CopilotChatResponse:
        """Tool: get_restock_recommendations"""
        cat_filter = args.get("category")
        filtered_prods = products
        if cat_filter:
            filtered_prods = [
                p for p in products
                if cat_filter.lower() in p.get("category", "").lower()
            ]

        low_stock = [
            p for p in filtered_prods
            if int(p.get("current_stock", 0)) <= int(p.get("reorder_threshold", 10))
        ]

        if not low_stock:
            return CopilotChatResponse(
                reply=f"**Inventory is Healthy!** All {len(filtered_prods)} products are above safety reorder thresholds. No immediate stockouts detected.",
                evidence=[
                    CopilotEvidenceItem(
                        source_metric="Healthy SKUs",
                        value=f"{len(filtered_prods)}/{len(filtered_prods)} OK",
                        context="All inventory lines comfortably above reorder points"
                    )
                ],
                draft_action=None,
                llm_configured=True,
                provider_info="LocalPulse Agent Tool: get_restock_recommendations",
            )

        lead = low_stock[0]
        rec_qty = max(20, int(lead.get("reorder_threshold", 10)) * 2)

        reply_lines = [
            f"**Restock Recommendations for {merchant.get('business_name', 'Store')}:**",
            f"Found **{len(low_stock)} product(s)** at or below their safety reorder thresholds:\n"
        ]
        for p in low_stock:
            curr = int(p.get("current_stock", 0))
            thresh = int(p.get("reorder_threshold", 10))
            unit = p.get("unit", "units")
            suggested = max(15, thresh * 2 - curr)
            reply_lines.append(
                f"- **{p.get('name')}**: Stock = **{curr} {unit}** (Safety Limit: {thresh} {unit}) -> Suggested Order: **+{suggested} {unit}**"
            )

        draft = DraftAction(
            action_type="RESTOCK_INVENTORY",
            title=f"Confirm Replenishment: {lead['name']}",
            description=f"Replenish +{rec_qty} {lead.get('unit', 'units')} for urgent stockout prevention.",
            payload={
                "product_id": lead["product_id"],
                "product_name": lead["name"],
                "quantity": rec_qty,
                "adjustment_type": "RESTOCK",
                "notes": "Generated by AI Copilot restock advisory",
            },
            requires_confirmation=True,
        )

        evidence = [
            CopilotEvidenceItem(
                source_metric="Urgent Stockout Warnings",
                value=f"{len(low_stock)} SKUs flagged",
                context=", ".join([p.get("name", "") for p in low_stock[:3]])
            )
        ]

        return CopilotChatResponse(
            reply="\n".join(reply_lines),
            evidence=evidence,
            draft_action=draft,
            llm_configured=True,
            provider_info="LocalPulse Agent Tool: get_restock_recommendations",
        )

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

    def execute_adjust_inventory_stock(
        self,
        args: dict,
        merchant: dict,
        products: List[dict]
    ) -> CopilotChatResponse:
        """Tool: adjust_inventory_stock (Proposes DraftAction)"""
        tool = "adjust_inventory_stock"
        p_name = args.get("product_name", "") or ""
        raw_qty = to_int(args.get("quantity", 0))
        qty = abs(raw_qty) if raw_qty is not None else None
        adj_type = normalize_adjustment_type(args.get("adjustment_type", "RESTOCK"))
        if adj_type is None:
            return self._clarify(
                f"Unknown adjustment type **'{args.get('adjustment_type')}'**. Use RESTOCK, DAMAGE_LOSS or AUDIT_CORRECTION.",
                tool,
            )
        notes = args.get("notes") or f"Requested via Copilot Agent ({adj_type})"

        target_p = self.find_product_by_name(p_name, products)
        picked_note = ""
        if not target_p and args.get("auto_select") == "most_urgent_restock" and products:
            # Most urgent = lowest stock relative to its reorder threshold
            def urgency(p):
                return int(p.get("current_stock", 0)) / max(1, int(p.get("reorder_threshold", 10)))
            target_p = min(products, key=urgency)
            picked_note = (
                f"*Your most urgent low-stock item is **{target_p['name']}** "
                f"({int(target_p.get('current_stock', 0))} left vs reorder level "
                f"{int(target_p.get('reorder_threshold', 10))}), so I picked it.*\n\n"
            )
        if not target_p:
            return self._product_not_found(p_name, products, tool, "restock or adjust")

        qty_error = check_quantity(qty)
        if qty_error:
            return self._clarify(
                f"{qty_error} How many {target_p.get('unit', 'units')} of **{target_p['name']}** should I adjust?",
                tool,
            )

        curr_stock = int(target_p.get("current_stock", 0))
        projected_stock = curr_stock + qty if adj_type == "RESTOCK" else max(0, curr_stock - qty)

        draft = DraftAction(
            action_type="RESTOCK_INVENTORY",
            title=f"Stock Adjustment: {target_p['name']} ({'+' if adj_type == 'RESTOCK' else '-'}{qty})",
            description=f"Adjust stock from {curr_stock} to {projected_stock} {target_p.get('unit', 'units')} ({adj_type}).",
            payload={
                "product_id": target_p["product_id"],
                "product_name": target_p["name"],
                "quantity": abs(qty),
                "adjustment_type": adj_type,
                "notes": notes,
            },
            requires_confirmation=True,
        )

        reply = (
            f"{picked_note}"
            f"**Drafted Inventory Movement Proposal:**\n\n"
            f"- **Product:** {target_p['name']} (`{target_p['product_id']}`)\n"
            f"- **Current Stock:** {curr_stock} {target_p.get('unit', 'units')}\n"
            f"- **Adjustment:** **{'+' if adj_type == 'RESTOCK' else '-'}{qty} {target_p.get('unit', 'units')}** ({adj_type})\n"
            f"- **Resulting Stock:** **{projected_stock} {target_p.get('unit', 'units')}**\n"
            f"- **Notes:** {notes}\n\n"
            f"*Note: Because modifying inventory updates persisted store accounts and audited logs, please review and click **Confirm & Apply** below.*"
        )

        return CopilotChatResponse(
            reply=reply,
            evidence=[
                CopilotEvidenceItem(
                    source_metric="Current Stock",
                    value=f"{curr_stock} {target_p.get('unit', 'units')}",
                    context=f"Threshold: {target_p.get('reorder_threshold', 10)}"
                )
            ],
            draft_action=draft,
            llm_configured=True,
            provider_info="LocalPulse Agent Tool: adjust_inventory_stock",
        )

    def execute_add_catalog_product(
        self,
        args: dict,
        merchant: dict,
        products: List[dict]
    ) -> CopilotChatResponse:
        """Tool: add_catalog_product (Proposes DraftAction)"""
        tool = "add_catalog_product"
        name = (args.get("name") or "").strip()
        category = (args.get("category") or "General").strip()
        cp = to_float(args.get("cost_price", 0.0))
        sp = to_float(args.get("selling_price", 0.0))
        init_stock = to_int(args.get("initial_stock", 20))
        threshold = to_int(args.get("reorder_threshold", 10))
        unit = args.get("unit") or "units"

        product_error = check_new_product(name, cp, sp)
        if product_error:
            return self._clarify(f"I haven't drafted this product yet: {product_error}", tool)
        if init_stock is None or init_stock < 0 or threshold is None or threshold < 0:
            return self._clarify("Initial stock and reorder threshold must be whole numbers of 0 or more.", tool)
        if any(p.get("name", "").strip().lower() == name.lower() for p in products):
            return self._clarify(
                f"**{name}** is already in your catalog. Want to restock it instead?", tool
            )

        margin_pct = round(((sp - cp) / sp * 100.0), 1) if sp > 0 else 0.0

        draft = DraftAction(
            action_type="ADD_PRODUCT",
            title=f"Add Catalog Product: {name}",
            description=f"Create new product SKU '{name}' in '{category}' (Cost: ₹{cp:,.2f}, Retail: ₹{sp:,.2f}, Initial Stock: {init_stock} {unit}).",
            payload={
                "name": name,
                "category": category,
                "cost_price": cp,
                "selling_price": sp,
                "current_stock": init_stock,
                "reorder_threshold": threshold,
                "unit": unit,
            },
            requires_confirmation=True,
        )

        reply = (
            f"**Drafted New Catalog SKU Proposal:**\n\n"
            f"- **Product Name:** **{name}**\n"
            f"- **Category:** {category}\n"
            f"- **Cost Price (Wholesale):** ₹{cp:,.2f}\n"
            f"- **Selling Price (Retail):** ₹{sp:,.2f}\n"
            f"- **Projected Gross Margin:** **{margin_pct}%**\n"
            f"- **Initial Intake Stock:** {init_stock} {unit} (Alert threshold: {threshold} {unit})\n\n"
            f"Click **Confirm & Apply** below to initialize this product in your catalog and log initial intake inventory."
        )

        return CopilotChatResponse(
            reply=reply,
            evidence=[
                CopilotEvidenceItem(
                    source_metric="New SKU Profit Margin",
                    value=f"{margin_pct}%",
                    context=f"CP ₹{cp:,.2f} -> SP ₹{sp:,.2f}"
                )
            ],
            draft_action=draft,
            llm_configured=True,
            provider_info="LocalPulse Agent Tool: add_catalog_product",
        )

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

        # duration_days is inclusive of the start day (a 7-day campaign ends 6 days after it starts),
        # matching how CampaignService computes duration from start/end dates.
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
            # "End the active campaign" with only one running: that's the one.
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

    # ── Chart helpers (minimal charts, shown only when the merchant asks) ──────
    @staticmethod
    def _short_labels(names: List[str]) -> List[str]:
        """Short chart labels: first two words without pack sizes ("Amul Taaza", "Tata Salt").
        Adds a third word when two labels would otherwise be identical."""
        def words(n: str) -> List[str]:
            return [w for w in re.sub(r"\(.*?\)", "", n).split() if not re.fullmatch(r"\d+[a-zA-Z]*", w)]
        labels = [" ".join(words(n)[:2]) or n for n in names]
        for i, lab in enumerate(labels):
            if labels.count(lab) > 1:
                labels[i] = " ".join(words(names[i])[:3]) or names[i]
        return [lab if len(lab) <= 22 else lab[:21] + "…" for lab in labels]

    def _product_chart(self, rows: List[Tuple[dict, float]], title: str, value_label: str, money: bool) -> ChartData:
        names = [p["name"] for p, _ in rows]
        return ChartData(
            kind="bars",
            title=title,
            value_label=value_label,
            value_prefix="₹" if money else "",
            points=[
                ChartPoint(label=lab, value=round(float(v), 2), full_label=name)
                for lab, name, (_, v) in zip(self._short_labels(names), names, rows)
            ],
        )

    # ── Sales analytics helpers ─────────────────────────────────────────────
    @staticmethod
    def _sale_profit(sale: dict, product: Optional[dict]) -> float:
        """Gross profit of one sales record (stored value, else revenue - cost)."""
        if sale.get("gross_profit") is not None:
            return float(sale.get("gross_profit") or 0.0)
        revenue = float(sale.get("revenue", 0.0))
        if sale.get("cogs") is not None:
            return revenue - float(sale.get("cogs") or 0.0)
        cost = float((product or {}).get("cost_price", 0.0))
        return revenue - cost * int(sale.get("units_sold", 0))

    def _period_totals(self, products: List[dict], sales: List[dict], period: Period) -> Dict[str, dict]:
        """Per-product totals inside the period. Products with no sales get zeros."""
        by_id = {p["product_id"]: p for p in products}
        totals = {pid: {"units": 0, "revenue": 0.0, "profit": 0.0} for pid in by_id}
        for s in sales:
            pid = s.get("product_id")
            if pid not in totals or not period.contains(s.get("date", "")):
                continue
            t = totals[pid]
            t["units"] += int(s.get("units_sold", 0))
            t["revenue"] += float(s.get("revenue", 0.0))
            t["profit"] += self._sale_profit(s, by_id[pid])
        return totals

    def _rank_products(
        self, products: List[dict], sales: List[dict], period: Period,
        rank_by: str = "units", order: str = "top",
    ) -> List[Tuple[dict, dict]]:
        totals = self._period_totals(products, sales, period)
        ranked = [(p, totals[p["product_id"]]) for p in products]
        ranked.sort(key=lambda pt: (pt[1][rank_by], pt[1]["revenue"]), reverse=(order != "bottom"))
        return ranked

    @staticmethod
    def _coverage_note(sales: List[dict], period: Period) -> str:
        """Warn when the period starts before the first recorded sale."""
        dates = [s.get("date") for s in sales if s.get("date")]
        if not dates:
            return "\n\n*No sales have been recorded yet.*"
        first = min(dates)
        if period.start_str < first:
            return f"\n\n*Note: sales records start on {first}, so earlier days in this period have no data.*"
        return ""

    @staticmethod
    def _indian(n: int) -> str:
        """Indian digit grouping, matching the dashboard: 286307 -> '2,86,307'."""
        sign, digits = ("-" if n < 0 else ""), str(abs(int(n)))
        if len(digits) <= 3:
            return sign + digits
        head, tail = digits[:-3], digits[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        return sign + ",".join(groups) + "," + tail

    def _money(self, x: float) -> str:
        return f"₹{self._indian(round(x))}" if abs(x) >= 100 else f"₹{x:,.2f}"

    @staticmethod
    def _change_text(current: float, previous: float, vs: str = "the previous period") -> str:
        if previous <= 0:
            return f"no data for {vs}" if current > 0 else "no change"
        pct = (current - previous) / previous * 100.0
        if abs(pct) < 0.5:
            return f"flat vs {vs}"
        return f"{'up' if pct > 0 else 'down'} {abs(pct):.1f}% vs {vs}"

    # ── Tool: get_top_products ──────────────────────────────────────────────
    def execute_get_top_products(
        self, args: dict, merchant: dict, products: List[dict], sales: List[dict],
    ) -> CopilotChatResponse:
        """Tool: get_top_products — rank all products by units, revenue or profit."""
        tool = "get_top_products"
        if not products:
            return self._clarify("Your catalog has no products yet, so there's nothing to rank.", tool)

        period = period_from_args(args, default_days=7)
        rank_by = str(args.get("rank_by") or "units").lower()
        if rank_by not in ("units", "revenue", "profit"):
            rank_by = "units"
        order = "bottom" if str(args.get("order") or "top").lower() == "bottom" else "top"
        max_limit = len(products) if order == "top" else max(1, len(products) // 2)
        limit = max(1, min(to_int(args.get("limit", 5)) or 5, max_limit))

        ranked = self._rank_products(products, sales, period, rank_by, order)
        shown = ranked[:limit]
        all_totals = [t for _, t in ranked]
        store_units = sum(t["units"] for t in all_totals)
        store_revenue = sum(t["revenue"] for t in all_totals)
        store_metric = sum(t[rank_by] for t in all_totals)

        if store_units == 0:
            return self._clarify(
                f"No sales were recorded for **{period.label.lower()}** ({period.range_text()})."
                + self._coverage_note(sales, period),
                tool,
            )

        metric_word = {"units": "units sold", "revenue": "revenue", "profit": "gross profit"}[rank_by]
        if order == "top":
            header = f"**Top Sellers Analysis: {period.label} ({period.range_text()})**"
            intro = f"Your {limit} best-performing product{'s' if limit != 1 else ''}, ranked by {metric_word}:"
        else:
            header = f"**Slowest Movers Analysis: {period.label} ({period.range_text()})**"
            intro = f"Your {limit} weakest product{'s' if limit != 1 else ''}, ranked by {metric_word} (lowest first):"

        lines = [header, "", intro]
        for i, (p, t) in enumerate(shown, start=1):
            unit = p.get("unit", "units")
            share = (t[rank_by] / store_metric * 100.0) if store_metric > 0 else 0.0
            if t["units"] == 0:
                lines.append(f"{i}. **{p['name']}**: no sales in this period")
                continue
            lines.append(
                f"{i}. **{p['name']}**: {t['units']} {unit} · {self._money(t['revenue'])} revenue · "
                f"{self._money(t['profit'])} profit ({share:.0f}% of store {metric_word})"
            )

        lines.append("")
        lines.append(
            f"Store total for this period: **{self._indian(store_units)} units** · **{self._money(store_revenue)}** revenue "
            f"across {len(products)} products."
        )
        if order == "bottom":
            lines.append("Tip: ask *\"Recommend clearance discounts for excess stock\"* to move slow items.")
        elif rank_by == "units":
            lines.append("Tip: units mix different pack sizes. Ask *\"top products by revenue\"* to compare in ₹.")
        reply = "\n".join(lines) + self._coverage_note(sales, period)

        chart = self._product_chart(
            [(p, t[rank_by]) for p, t in shown],
            title=f"{'Top' if order == 'top' else 'Slowest'} products by {metric_word} · {period.label}",
            value_label=metric_word.capitalize(),
            money=rank_by != "units",
        )

        lead_p, lead_t = shown[0]
        evidence = [
            CopilotEvidenceItem(
                source_metric="#1 " + ("Top Seller" if order == "top" else "Slowest Mover"),
                value=lead_p["name"][:40],
                context=f"{lead_t['units']} {lead_p.get('unit', 'units')} · {self._money(lead_t['revenue'])}",
            ),
            CopilotEvidenceItem(
                source_metric=f"Store Revenue ({period.label})",
                value=self._money(store_revenue),
                context=f"{store_units} units, {period.range_text()}",
            ),
        ]
        return CopilotChatResponse(
            reply=reply, evidence=evidence, draft_action=None, chart=chart,
            llm_configured=True, provider_info=f"LocalPulse Agent Tool: {tool}",
        )

    # ── Tool: get_sales_summary ─────────────────────────────────────────────
    def execute_get_sales_summary(
        self, args: dict, merchant: dict, products: List[dict], sales: List[dict],
    ) -> CopilotChatResponse:
        """Tool: get_sales_summary — store totals for a period vs the previous period."""
        tool = "get_sales_summary"
        period = period_from_args(args, default_days=7)
        prev = period.previous()
        by_id = {p["product_id"]: p for p in products}

        cur = [s for s in sales if s.get("product_id") in by_id and period.contains(s.get("date", ""))]
        old = [s for s in sales if s.get("product_id") in by_id and prev.contains(s.get("date", ""))]

        def sums(rows):
            return (
                sum(float(s.get("revenue", 0.0)) for s in rows),
                sum(int(s.get("units_sold", 0)) for s in rows),
                sum(self._sale_profit(s, by_id.get(s.get("product_id"))) for s in rows),
            )

        revenue, units, profit = sums(cur)
        prev_revenue, prev_units, _ = sums(old)

        if units == 0:
            return self._clarify(
                f"No sales were recorded for **{period.label.lower()}** ({period.range_text()})."
                + self._coverage_note(sales, period),
                tool,
            )

        margin = (profit / revenue * 100.0) if revenue > 0 else 0.0
        daily_avg = revenue / period.days

        # Best day by revenue
        by_day: Dict[str, float] = {}
        for s in cur:
            by_day[s["date"]] = by_day.get(s["date"], 0.0) + float(s.get("revenue", 0.0))
        best_day, best_day_rev = max(by_day.items(), key=lambda kv: kv[1])
        best_day_d = date.fromisoformat(best_day)
        best_day_txt = f"{best_day_d.strftime('%a')} {best_day_d.day} {best_day_d.strftime('%b')}"

        top_p, top_t = self._rank_products(products, sales, period, rank_by="revenue")[0]

        lines = [
            f"**Sales Summary Overview: {period.label} ({period.range_text()})**",
            "",
            f"- **Revenue:** **{self._money(revenue)}** ({self._change_text(revenue, prev_revenue, 'the ' + prev.label)})",
            f"- **Units sold:** **{self._indian(units)}** ({self._change_text(units, prev_units, 'the ' + prev.label)})",
            f"- **Gross profit:** **{self._money(profit)}** ({margin:.1f}% margin)",
        ]
        if period.days > 1:
            lines.append(f"- **Daily average:** {self._money(daily_avg)} per day")
            lines.append(f"- **Best day:** {best_day_txt}: {self._money(best_day_rev)}")
        share = (top_t["revenue"] / revenue * 100.0) if revenue > 0 else 0.0
        lines.append(
            f"- **Top product:** {top_p['name']}: {self._money(top_t['revenue'])} ({share:.0f}% of revenue)"
        )
        lines.append("")
        lines.append(f"Compared with the {prev.label} ({prev.range_text()}).")
        lines.append("Ask *\"top products " + period.label.lower() + "\"* for the full product ranking.")
        reply = "\n".join(lines) + self._coverage_note(sales, period)

        if period.days == 1:
            ranked_day = [(p, t["revenue"]) for p, t in self._rank_products(products, sales, period, rank_by="revenue")]
            chart = self._product_chart(
                [r for r in ranked_day if r[1] > 0][:8],
                title=f"Revenue by product · {period.label}", value_label="Revenue", money=True,
            )
        else:
            days_list = [period.start + timedelta(days=i) for i in range(period.days)]
            if period.days <= 31:
                buckets = [(f"{d.strftime('%a')} {d.day}" if period.days <= 7 else f"{d.day} {d.strftime('%b')}",
                            d.strftime("%a %d %b %Y"), [d]) for d in days_list]
            else:  # long periods: one column per week
                buckets = []
                for i in range(0, len(days_list), 7):
                    wk = days_list[i:i + 7]
                    buckets.append((f"{wk[0].day} {wk[0].strftime('%b')}",
                                    f"Week of {wk[0].strftime('%d %b')} – {wk[-1].strftime('%d %b')}", wk))
            chart = ChartData(
                kind="columns",
                title=f"Daily revenue · {period.label}" if period.days <= 31 else f"Weekly revenue · {period.label}",
                value_label="Revenue",
                value_prefix="₹",
                points=[
                    ChartPoint(label=lab, value=round(sum(by_day.get(d.isoformat(), 0.0) for d in ds), 2), full_label=full)
                    for lab, full, ds in buckets
                ],
            )

        evidence = [
            CopilotEvidenceItem(
                source_metric=f"Revenue ({period.label})",
                value=self._money(revenue),
                context=self._change_text(revenue, prev_revenue, "the " + prev.label),
            ),
            CopilotEvidenceItem(
                source_metric="Gross Profit",
                value=self._money(profit),
                context=f"{margin:.1f}% margin on {units} units",
            ),
        ]
        return CopilotChatResponse(
            reply=reply, evidence=evidence, draft_action=None, chart=chart,
            llm_configured=True, provider_info=f"LocalPulse Agent Tool: {tool}",
        )

    # ── Tool: compare_products ──────────────────────────────────────────────
    def execute_compare_products(
        self, args: dict, merchant: dict, products: List[dict], sales: List[dict],
    ) -> CopilotChatResponse:
        """Tool: compare_products — side-by-side comparison of named products."""
        tool = "compare_products"
        names = args.get("product_names") or []
        if isinstance(names, str):
            names = [n for n in re.split(r",|\band\b|\bvs\.?\b|\bversus\b", names) if n.strip()]

        chosen: List[dict] = []
        missing: List[str] = []
        for n in names:
            p = self.find_product_by_name(str(n), products)
            if p and p not in chosen:
                chosen.append(p)
            elif not p:
                missing.append(str(n).strip())

        if len(chosen) < 2:
            available = ", ".join(p.get("name", "") for p in products[:6])
            miss = f" I couldn't find: {', '.join(missing)}." if missing else ""
            return self._clarify(
                f"Tell me at least two products to compare.{miss}\nYour catalog includes: {available}.", tool
            )

        period = period_from_args(args, default_days=7)
        prev = period.previous()
        cur_t = self._period_totals(chosen, sales, period)
        prev_t = self._period_totals(chosen, sales, prev)

        lines = [f"**Product Comparison Analysis: {period.label} ({period.range_text()})**", ""]
        for p in chosen:
            t, pt = cur_t[p["product_id"]], prev_t[p["product_id"]]
            unit = p.get("unit", "units")
            lines.append(f"- **{p['name']}**")
            lines.append(
                f"-> {t['units']} {unit} sold · {self._money(t['revenue'])} revenue · "
                f"{self._money(t['profit'])} profit · {self._change_text(t['revenue'], pt['revenue'], 'the ' + prev.label)}"
            )
            lines.append(
                f"-> Avg {t['units'] / period.days:.1f} {unit}/day · stock on hand {int(p.get('current_stock', 0))} {unit}"
            )

        ranked = sorted(chosen, key=lambda p: cur_t[p["product_id"]]["revenue"], reverse=True)
        lead, second = ranked[0], ranked[1]
        diff = cur_t[lead["product_id"]]["revenue"] - cur_t[second["product_id"]]["revenue"]
        lines.append("")
        lines.append(
            f"**{lead['name']}** earned the most revenue, {self._money(diff)} more than {second['name']}."
        )
        if missing:
            lines.append(f"*Not found in your catalog: {', '.join(missing)}.*")
        reply = "\n".join(lines) + self._coverage_note(sales, period)

        chart = self._product_chart(
            [(p, cur_t[p["product_id"]]["revenue"]) for p in chosen],
            title=f"Revenue comparison · {period.label}", value_label="Revenue", money=True,
        )
        evidence = [
            CopilotEvidenceItem(
                source_metric=f"Revenue ({period.label})",
                value=self._money(cur_t[p["product_id"]]["revenue"]),
                context=p["name"][:40],
            )
            for p in chosen[:3]
        ]
        return CopilotChatResponse(
            reply=reply, evidence=evidence, draft_action=None, chart=chart,
            llm_configured=True, provider_info=f"LocalPulse Agent Tool: {tool}",
        )

    def execute_get_business_overview(
        self,
        merchant: dict,
        products: List[dict],
        sales: List[dict],
        campaigns: List[dict]
    ) -> CopilotChatResponse:
        """Tool: get_business_overview"""
        # Last 30 calendar days (previously: the latest 300 records, whatever dates they covered)
        last_30 = last_n_days(30)
        window = [s for s in sales if last_30.contains(s.get("date", ""))]
        total_30d_rev = sum(float(s.get("revenue", 0.0)) for s in window)
        total_units = sum(int(s.get("units_sold", 0)) for s in window)
        low_stock = [
            p for p in products
            if int(p.get("current_stock", 0)) <= int(p.get("reorder_threshold", 10))
        ]
        active_camps = [c for c in campaigns if c.get("status") == "ACTIVE"]

        reply = (
            f"**Operational Overview for {merchant.get('business_name', 'Store')}:**\n\n"
            f"- **Category:** {merchant.get('category', 'Retail')}\n"
            f"- **Active Catalog Lines:** **{len(products)} products**\n"
            f"- **Sales, Last 30 Days:** **{total_units} units** (Revenue: **₹{total_30d_rev:,.2f}**)\n"
            f"- **Inventory Alerts:** **{len(low_stock)} product(s)** below safety reorder thresholds\n"
            f"- **Active Promotions:** **{len(active_camps)} campaign(s)** running\n\n"
            f"**Available Agent Actions you can ask me to do:**\n"
            f"• *'What are my top selling products this week?'*\n"
            f"• *'How much did I sell yesterday?'*\n"
            f"• *'Compare [Product A] and [Product B] sales'*\n"
            f"• *'Analyze performance of [Product Name] over last 14 days'*\n"
            f"• *'Restock [Product Name] by 30 units'*\n"
            f"• *'Which items are low and need restocking?'*\n"
            f"• *'Recommend discount strategies for excess stock'*\n"
            f"• *'Add new product [Name] category [Category] cost 50 selling 80 stock 40'*\n"
            f"• *'Draft a weekend discount campaign for [Product]'*\n"
            f"• *'End active campaign [Title]'*"
        )

        evidence = [
            CopilotEvidenceItem(
                source_metric="Revenue, Last 30 Days",
                value=f"₹{total_30d_rev:,.2f}",
                context=f"{last_30.range_text()}, {total_units} units"
            ),
            CopilotEvidenceItem(
                source_metric="Active Catalog",
                value=f"{len(products)} SKUs",
                context=f"{len(low_stock)} items need restock"
            )
        ]

        return CopilotChatResponse(
            reply=reply,
            evidence=evidence,
            draft_action=None,
            llm_configured=True,
            provider_info="LocalPulse Agent Tool: get_business_overview",
        )

    def execute_unmapped_fallback(self, query: str, products: Optional[List[dict]] = None) -> CopilotChatResponse:
        """Fallback when user intent cannot be mapped to any operational tool."""
        # Use the merchant's own product names in the examples
        names = [p.get("name", "") for p in (products or []) if p.get("name")]
        a = names[0] if names else "Milk"
        b = names[1] if len(names) > 1 else "Bread"
        short = lambda n: " ".join(n.split()[:3])
        a, b = short(a), short(b)
        reply = (
            f"**I couldn't match that to a store action yet**\n\n"
            f"I'm not sure how to answer *\"{query}\"*. Try asking it like one of these:\n\n"
            f"Here are the things I can do for your store:\n"
            f"1. **Top / Slow Sellers:** *\"What are my top selling products this week?\"* or *\"Which items are not selling?\"*\n"
            f"2. **Sales Summary:** *\"How much did I sell yesterday?\"* or *\"Sales for the last 30 days\"*\n"
            f"3. **Compare Products:** *\"Compare {a} and {b} sales\"*\n"
            f"4. **Product Analytics:** *\"Analyze {a} sales over the last 14 days\"*\n"
            f"5. **Restock Inventory:** *\"Restock {a} by 25 units\"* or *\"Which items need restock?\"*\n"
            f"6. **Clearance Discounts:** *\"Recommend discounts to clear surplus inventory\"*\n"
            f"7. **Launch / End Campaign:** *\"Draft a 10% weekend offer on {b}\"* or *\"End active campaign\"*\n"
            f"8. **Add New Product:** *\"Add new product Greek Yogurt, cost 45, sell 70, stock 30\"*\n"
            f"9. **Store Overview:** *\"Show me my business snapshot\"*"
        )

        return CopilotChatResponse(
            reply=reply,
            evidence=[],
            draft_action=None,
            llm_configured=True,
            provider_info="LocalPulse Agent: Unmapped Intent Fallback",
        )


copilot_tool_executor = CopilotToolExecutor()
