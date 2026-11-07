"""
Inventory and catalog execution mixin for Copilot Agent tools:
- get_catalog_products
- get_restock_recommendations
- adjust_inventory_stock
- add_catalog_product
"""

from typing import List
from app.schemas.copilot import (
    CopilotChatResponse, CopilotEvidenceItem, DraftAction,
)
from app.services.copilot.guards import (
    to_float, to_int, normalize_adjustment_type, check_quantity, check_new_product,
)


class InventoryExecutorMixin:
    """Handles inventory queries, restock advisories, adjustments, and catalog SKUs."""

    # ── Tool: get_catalog_products ──────────────────────────────────────────
    def execute_get_catalog_products(
        self,
        args: dict,
        merchant: dict,
        products: List[dict]
    ) -> CopilotChatResponse:
        """Tool: get_catalog_products — lists active catalog products with current stock & pricing."""
        cat_filter = (args.get("category") or "").strip().lower()
        matched = [
            p for p in products
            if not cat_filter or cat_filter in p.get("category", "").lower()
        ]
        if not matched:
            return CopilotChatResponse(
                reply=f"No products found in your catalog{' for category ' + cat_filter.title() if cat_filter else ''}.",
                evidence=[],
                draft_action=None,
                llm_configured=True,
                provider_info="LocalPulse Agent Tool: get_catalog_products",
            )

        lines = [
            f"**Catalog Inventory for {merchant.get('business_name', 'Your Store')}:**\n",
            f"Found **{len(matched)} product(s)** in your active catalog:\n"
        ]
        for idx, p in enumerate(matched, 1):
            name = p.get("name", "Product")
            cat = p.get("category", "General")
            stock = int(p.get("current_stock", 0))
            sp = float(p.get("selling_price", 0.0))
            threshold = int(p.get("reorder_threshold", 10))
            unit = p.get("unit", "units")
            stock_badge = "CRITICAL LOW" if stock <= 5 else ("WARNING" if stock <= threshold else "HEALTHY")
            lines.append(
                f"{idx}. **{name}** ({cat})\n"
                f"   - Retail Price: **₹{sp:,.2f}** · On-hand Stock: **{stock} {unit}** ({stock_badge})"
            )

        lines.append("\n*Tip: To replenish stock or adjust items, try asking \"Restock [Product] by 20 units\" or \"Show 7-day demand forecast\".*")
        reply = "\n".join(lines)
        evidence = [
            CopilotEvidenceItem(
                source_metric="Active SKUs",
                value=f"{len(matched)} items",
                context=merchant.get("business_name", "Store")
            ),
            CopilotEvidenceItem(
                source_metric="Total Inventory Units",
                value=f"{sum(int(p.get('current_stock', 0)) for p in matched):,} units",
                context="On-hand warehouse/storefront stock"
            )
        ]
        return CopilotChatResponse(
            reply=reply,
            evidence=evidence,
            draft_action=None,
            llm_configured=True,
            provider_info="LocalPulse Agent Tool: get_catalog_products"
        )

    # ── Tool: get_restock_recommendations ───────────────────────────────────
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

    # ── Tool: adjust_inventory_stock ────────────────────────────────────────
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

    # ── Tool: add_catalog_product ───────────────────────────────────────────
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
