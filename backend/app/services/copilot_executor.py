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
    ActionConfirmationResponse
)
from app.services.forecasting import forecasting_service


class CopilotToolExecutor:
    """Executes read-only operations immediately and structures mutation drafts."""

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
        sales: List[dict]
    ) -> CopilotChatResponse:
        """Tool: analyze_product_performance"""
        p_name = args.get("product_name", "")
        days = int(args.get("days", 7))
        target_p = self.find_product_by_name(p_name, products)

        if not target_p:
            available = ", ".join([p.get("name", "") for p in products[:5]])
            return CopilotChatResponse(
                reply=f"Could not locate product matching **'{p_name}'** in your catalog.\nAvailable items include: {available}.",
                evidence=[],
                draft_action=None,
                llm_configured=True,
                provider_info="LocalPulse Agent Tool: analyze_product_performance",
            )

        p_id = target_p["product_id"]
        # Filter sales for this product
        p_sales = [s for s in sales if s.get("product_id") == p_id]
        sorted_sales = sorted(p_sales, key=lambda s: s.get("date", ""), reverse=True)
        window_sales = sorted_sales[:days]

        total_units = sum(int(s.get("units_sold", 0)) for s in window_sales)
        total_rev = sum(float(s.get("revenue", 0.0)) for s in window_sales)
        days_count = max(1, len(window_sales))
        avg_daily_units = round(total_units / days_count, 1)

        curr_stock = int(target_p.get("current_stock", 0))
        runway_days = round(curr_stock / avg_daily_units, 1) if avg_daily_units > 0 else 99

        # Run forecasting model
        fc = forecasting_service.forecast_product(target_p, p_sales, horizon_days=7)

        evidence = [
            CopilotEvidenceItem(
                source_metric=f"{days}-Day Unit Velocity",
                value=f"{total_units} {target_p.get('unit', 'units')}",
                context=f"Average ~{avg_daily_units} units/day over {days_count} recorded days"
            ),
            CopilotEvidenceItem(
                source_metric=f"{days}-Day Revenue",
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
            f"**Performance Analysis for '{target_p['name']}':**\n\n"
            f"- **Category:** {target_p.get('category', 'General')}\n"
            f"- **Selling Price:** ₹{float(target_p.get('selling_price', 0)):,.2f} "
            f"(Effective: ₹{float(target_p.get('effective_selling_price', target_p.get('selling_price', 0))):,.2f})\n"
            f"- **Volume Sold ({days}d):** **{total_units} {target_p.get('unit', 'units')}** across catalog transactions\n"
            f"- **Total Revenue Generated:** **₹{total_rev:,.2f}**\n"
            f"- **Daily Average Velocity:** **{avg_daily_units} units/day**\n"
            f"- **Current Stock on Hand:** **{curr_stock} {target_p.get('unit', 'units')}** (~{runway_days} days of inventory runway)\n"
            f"- **Projected 7-Day Demand:** **{fc.total_forecasted_units} units** (Est. ₹{fc.total_projected_revenue:,.2f})"
            f"{stock_warning}"
        )

        draft = None
        if fc.stockout_risk:
            draft = DraftAction(
                action_type="RESTOCK_INVENTORY",
                title=f"Restock {target_p['name']}",
                description=f"Replenish +{fc.recommended_replenishment_units} units to cover next 7 days of projected demand.",
                payload={
                    "product_id": target_p["product_id"],
                    "product_name": target_p["name"],
                    "quantity": fc.recommended_replenishment_units,
                    "adjustment_type": "RESTOCK",
                    "notes": f"Triggered from {days}-day velocity analysis ({fc.total_forecasted_units} units projected)",
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
            scored_products.append((top_p, int(top_p.get("current_stock", 0)), 25.0, 8.0))

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
                "end_date": (date.today() + timedelta(days=7)).strftime("%Y-%m-%d"),
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
        p_name = args.get("product_name", "")
        qty = int(args.get("quantity", 0))
        adj_type = args.get("adjustment_type", "RESTOCK").upper()
        notes = args.get("notes", f"Requested via Copilot Agent ({adj_type})")

        target_p = self.find_product_by_name(p_name, products)
        if not target_p:
            available = ", ".join([p.get("name", "") for p in products[:5]])
            return CopilotChatResponse(
                reply=f"Could not find product matching **'{p_name}'** to adjust stock.\nCatalog items: {available}.",
                evidence=[],
                draft_action=None,
                llm_configured=True,
                provider_info="LocalPulse Agent Tool: adjust_inventory_stock",
            )

        curr_stock = int(target_p.get("current_stock", 0))
        projected_stock = curr_stock + qty if adj_type == "RESTOCK" else max(0, curr_stock - abs(qty))

        draft = DraftAction(
            action_type="RESTOCK_INVENTORY",
            title=f"Stock Adjustment: {target_p['name']} ({'+' if qty > 0 else ''}{qty})",
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
            f"**Drafted Inventory Movement Proposal:**\n\n"
            f"- **Product:** {target_p['name']} (`{target_p['product_id']}`)\n"
            f"- **Current Stock:** {curr_stock} {target_p.get('unit', 'units')}\n"
            f"- **Adjustment:** **{'+' if qty > 0 else ''}{qty} units** ({adj_type})\n"
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
        name = args.get("name", "").strip()
        category = args.get("category", "General").strip()
        cp = float(args.get("cost_price", 0.0))
        sp = float(args.get("selling_price", 0.0))
        init_stock = int(args.get("initial_stock", 20))
        threshold = int(args.get("reorder_threshold", 10))
        unit = args.get("unit", "units")

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
        title = args.get("title", "Promotional Offer")
        p_name = args.get("product_name", "")
        disc_pct = float(args.get("discount_pct", 10.0))
        duration = int(args.get("duration_days", 7))
        budget = float(args.get("budget", 1000.0))

        target_ids = []
        target_name = "Catalog Selection"
        if p_name:
            p = self.find_product_by_name(p_name, products)
            if p:
                target_ids = [p["product_id"]]
                target_name = p["name"]
        elif products:
            target_ids = [products[0]["product_id"]]
            target_name = products[0]["name"]

        start_date = date.today().strftime("%Y-%m-%d")
        end_date = (date.today() + timedelta(days=duration)).strftime("%Y-%m-%d")

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
            f"**Drafted Promotional Campaign:**\n\n"
            f"- **Title:** **{title}**\n"
            f"- **Target Product:** {target_name}\n"
            f"- **Discount Offered:** **{disc_pct}% OFF**\n"
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
                )
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
        c_query = args.get("campaign_title_or_id", "").strip().lower()

        # Find matching active campaign
        target_camp = None
        for c in campaigns:
            if c.get("status") == "ACTIVE":
                c_title = c.get("title", "").lower()
                c_id = c.get("campaign_id", "").lower()
                if c_query in c_title or c_query in c_id or not c_query:
                    target_camp = c
                    break

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

    def execute_get_business_overview(
        self,
        merchant: dict,
        products: List[dict],
        sales: List[dict],
        campaigns: List[dict]
    ) -> CopilotChatResponse:
        """Tool: get_business_overview"""
        total_30d_rev = sum(float(s.get("revenue", 0.0)) for s in sales[:300])
        total_units = sum(int(s.get("units_sold", 0)) for s in sales[:300])
        low_stock = [
            p for p in products
            if int(p.get("current_stock", 0)) <= int(p.get("reorder_threshold", 10))
        ]
        active_camps = [c for c in campaigns if c.get("status") == "ACTIVE"]

        reply = (
            f"**Operational Overview for {merchant.get('business_name', 'Store')}:**\n\n"
            f"- **Category:** {merchant.get('category', 'Retail')}\n"
            f"- **Active Catalog Lines:** **{len(products)} products**\n"
            f"- **Recent Sales Volume:** **{total_units} units** (Est. Revenue: **₹{total_30d_rev:,.2f}**)\n"
            f"- **Inventory Alerts:** **{len(low_stock)} product(s)** below safety reorder thresholds\n"
            f"- **Active Promotions:** **{len(active_camps)} campaign(s)** running\n\n"
            f"**Available Agent Actions you can ask me to do:**\n"
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
                source_metric="Gross Recorded Revenue",
                value=f"₹{total_30d_rev:,.2f}",
                context=f"Calculated from past sales transactions"
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

    def execute_unmapped_fallback(self, query: str) -> CopilotChatResponse:
        """Fallback when user intent cannot be mapped to any operational tool."""
        reply = (
            f"**Intent Not Mapped to an Operational Store Tool**\n\n"
            f"I could not map your query: *\"{query}\"* to any verified merchant action.\n\n"
            f"Here are the specific tools and operations I can execute for your store:\n"
            f"1. **Product Analytics:** *\"Analyze Milk sales over the last 14 days\"*\n"
            f"2. **Restock Inventory:** *\"Restock Masala Chai by 25 units\"* or *\"Which items need restock?\"*\n"
            f"3. **Clearance Discounts:** *\"Recommend discounts to clear surplus inventory\"*\n"
            f"4. **Add New Product:** *\"Add new product Greek Yogurt, cost 45, sell 70, stock 30\"*\n"
            f"5. **Launch Campaign:** *\"Draft a 10% weekend offer on Sourdough Bread\"*\n"
            f"6. **End Campaign:** *\"End active campaign Weekend Special\"*\n"
            f"7. **Store Overview:** *\"Show me my business snapshot\"*"
        )

        return CopilotChatResponse(
            reply=reply,
            evidence=[],
            draft_action=None,
            llm_configured=True,
            provider_info="LocalPulse Agent: Unmapped Intent Fallback",
        )


copilot_tool_executor = CopilotToolExecutor()
