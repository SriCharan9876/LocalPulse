"""
LocalPulse AI Business Copilot Orchestration Service.
Agentic architecture: maps natural language to operational tools,
executes read analytics immediately, and creates audited DraftActions for store mutations.
"""

import logging
import re
import uuid
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.schemas.copilot import (
    CopilotChatResponse, CopilotEvidenceItem, DraftAction,
    ActionConfirmationResponse, ChartData,
)
from app.services.copilot_parser import agent_tool_parser, CHART_WORDS
from app.services.copilot_executor import copilot_tool_executor
from app.services.action_guards import (
    to_float, to_int, normalize_adjustment_type, check_quantity,
    check_discount, check_discount_vs_cost, check_new_product,
)
from app.core.config import settings

logger = logging.getLogger(__name__)


class CopilotService:
    async def process_chat(
        self,
        query: str,
        merchant: dict,
        products: List[dict],
        recent_sales: List[dict],
        campaigns: List[dict],
        collaborations: List[dict],
        history: Optional[List[dict]] = None,
        events: Optional[List[dict]] = None,
    ) -> CopilotChatResponse:
        """
        Agentic Copilot Entrypoint:
        1. Analyzes user query and maps to an operational tool (via LLM or deterministic fallback with chat memory).
        2. If unmapped, returns transparent explanation of supported store capabilities.
        3. If mapped to a tool, executes analytical retrieval or returns a draft action for merchant confirmation.
        """
        tool_name, tool_args = await agent_tool_parser.parse_intent(
            query=query,
            products=products,
            campaigns=campaigns,
            history=history,
        )

        logger.info(f"Copilot query '{query}' mapped to tool: '{tool_name}' with args {tool_args}")

        # "yes" / "show chart" after an answer: re-send that answer's chart, opened
        if tool_name == "show_chart":
            return self._show_previous_chart(history)

        # "yes" right after a drafted action: changes are only applied with the button
        if tool_name is None and re.fullmatch(r"(yes|yeah|yep|sure|ok|okay|do it|go ahead|confirm|apply|haan)[.! ]*",
                                              query.lower().strip()):
            last = next((m for m in reversed(history or []) if m.get("role") == "assistant"), None)
            draft = (last or {}).get("draft_action") or {}
            if draft.get("status") == "PENDING_CONFIRMATION":
                return CopilotChatResponse(
                    reply=(f"To apply **{draft.get('title', 'this action')}**, click **Confirm & Apply** on the "
                           "draft card above. I never change your store data without that click."),
                    evidence=[], draft_action=None, llm_configured=True,
                    provider_info="LocalPulse Agent: Confirmation Guide",
                )

        response = self._dispatch(tool_name, tool_args, query, merchant, products, recent_sales,
                                  campaigns, events)

        # Charts are shown on request only. If the merchant already asked for a chart
        # ("... give me a vs chart") open it straight away; otherwise offer it.
        if response.chart is not None:
            if CHART_WORDS.search(query.lower()):
                response.chart.auto_open = True
            else:
                response.reply += "\n\n*Want to see this as a chart? Tap **Show chart** below or reply \"yes\".*"
        return response

    def _show_previous_chart(self, history: Optional[List[dict]]) -> CopilotChatResponse:
        last = next((m for m in reversed(history or []) if m.get("role") == "assistant" and m.get("chart")), None)
        if not last:
            return copilot_tool_executor.execute_unmapped_fallback(query="show chart")
        chart = ChartData(**last["chart"])
        chart.auto_open = True
        return CopilotChatResponse(
            reply=f"Here's the chart: **{chart.title}**.",
            evidence=[],
            draft_action=None,
            chart=chart,
            llm_configured=True,
            provider_info="LocalPulse Agent: Chart View",
        )

    def _dispatch(
        self,
        tool_name: Optional[str],
        tool_args: Dict[str, Any],
        query: str,
        merchant: dict,
        products: List[dict],
        recent_sales: List[dict],
        campaigns: List[dict],
        events: Optional[List[dict]],
    ) -> CopilotChatResponse:
        """Run the selected tool."""

        # Dispatch based on tool name
        if tool_name == "analyze_product_performance":
            return copilot_tool_executor.execute_analyze_product(
                args=tool_args,
                merchant=merchant,
                products=products,
                sales=recent_sales,
                events=events,
            )

        elif tool_name == "get_restock_recommendations":
            return copilot_tool_executor.execute_get_restock_recommendations(
                args=tool_args,
                merchant=merchant,
                products=products,
                sales=recent_sales
            )

        elif tool_name == "get_discount_recommendations":
            return copilot_tool_executor.execute_get_discount_recommendations(
                args=tool_args,
                merchant=merchant,
                products=products,
                sales=recent_sales
            )

        elif tool_name == "adjust_inventory_stock":
            return copilot_tool_executor.execute_adjust_inventory_stock(
                args=tool_args,
                merchant=merchant,
                products=products
            )

        elif tool_name == "add_catalog_product":
            return copilot_tool_executor.execute_add_catalog_product(
                args=tool_args,
                merchant=merchant,
                products=products
            )

        elif tool_name == "create_promotional_campaign":
            return copilot_tool_executor.execute_create_promotional_campaign(
                args=tool_args,
                merchant=merchant,
                products=products
            )

        elif tool_name == "end_promotional_campaign":
            return copilot_tool_executor.execute_end_promotional_campaign(
                args=tool_args,
                merchant=merchant,
                campaigns=campaigns
            )

        elif tool_name == "get_top_products":
            return copilot_tool_executor.execute_get_top_products(
                args=tool_args, merchant=merchant, products=products, sales=recent_sales
            )

        elif tool_name == "get_sales_summary":
            return copilot_tool_executor.execute_get_sales_summary(
                args=tool_args, merchant=merchant, products=products, sales=recent_sales
            )

        elif tool_name == "compare_products":
            return copilot_tool_executor.execute_compare_products(
                args=tool_args, merchant=merchant, products=products, sales=recent_sales
            )

        elif tool_name == "get_business_overview":
            return copilot_tool_executor.execute_get_business_overview(
                merchant=merchant,
                products=products,
                sales=recent_sales,
                campaigns=campaigns
            )

        else:
            # Query cannot be mapped to any operational tool
            return copilot_tool_executor.execute_unmapped_fallback(query=query, products=products)

    async def execute_confirmed_action(
        self,
        action_type: str,
        payload: dict,
        merchant: dict,
        db: AsyncIOMotorDatabase
    ) -> ActionConfirmationResponse:
        """
        Executes audited DB write operations ONLY after merchant explicitly confirms.
        Supports:
        - RESTOCK_INVENTORY
        - ADD_PRODUCT
        - CREATE_CAMPAIGN
        - END_CAMPAIGN
        """
        m_id = merchant["merchant_id"]
        now = datetime.utcnow()
        payload = payload or {}

        # The payload comes back from the client, so every rule is re-checked here
        # before any write (the draft-time checks in copilot_executor can be bypassed).
        def fail(message: str) -> ActionConfirmationResponse:
            return ActionConfirmationResponse(
                success=False, message=message, executed_action_type=action_type
            )

        # ── 1. RESTOCK / ADJUST INVENTORY ────────────────────────────────────
        if action_type == "RESTOCK_INVENTORY":
            p_id = payload.get("product_id")
            qty = to_int(payload.get("quantity", 0))
            adj_type = normalize_adjustment_type(payload.get("adjustment_type", "RESTOCK"))
            notes = payload.get("notes") or "Replenished via AI Copilot confirmed draft"

            qty_error = check_quantity(qty)
            if qty_error:
                return fail(qty_error)
            if adj_type is None:
                return fail("Adjustment type must be RESTOCK, DAMAGE_LOSS or AUDIT_CORRECTION.")

            product = None
            if p_id:
                product = await db.products.find_one({"merchant_id": m_id, "product_id": p_id})
            
            # Fallback to name search if product_id was not found (or drafted with name)
            p_name = payload.get("product_name")
            if not product and p_name and str(p_name).strip():
                # re.escape: product names like "Atta (5kg" or ".*" must be matched literally,
                # not as regex patterns (previously crashed with a 500 / matched everything).
                product = await db.products.find_one({
                    "merchant_id": m_id,
                    "name": {"$regex": re.escape(str(p_name).strip()), "$options": "i"}
                })
                if product:
                    p_id = product["product_id"]

            if not product:
                return ActionConfirmationResponse(
                    success=False,
                    message=f"Product '{p_name or p_id}' not found in current merchant catalog.",
                    executed_action_type=action_type
                )

            old_stock = int(product.get("current_stock", 0))
            new_stock = old_stock + qty if adj_type == "RESTOCK" else max(0, old_stock - qty)

            await db.products.update_one(
                {"merchant_id": m_id, "product_id": p_id},
                {"$set": {"current_stock": new_stock, "updated_at": now}}
            )

            # Insert audited movement log
            mov_doc = {
                "movement_id": f"mov-{m_id[:8]}-{p_id[:8]}-{int(now.timestamp())}",
                "merchant_id": m_id,
                "product_id": p_id,
                "product_name": product["name"],
                "adjustment_type": adj_type,
                "quantity_change": qty if adj_type == "RESTOCK" else -qty,
                "stock_before": old_stock,
                "stock_after": new_stock,
                "notes": notes,
                "created_at": now,
                "is_synthetic": True,
            }
            await db.inventory_movements.insert_one(mov_doc)

            return ActionConfirmationResponse(
                success=True,
                message=f"Successfully updated inventory for '{product['name']}'. Stock adjusted from {old_stock} to {new_stock} {product.get('unit', 'units')}.",
                executed_action_type=action_type,
                result_data={"product_id": p_id, "new_stock": new_stock}
            )

        # ── 2. ADD NEW PRODUCT TO CATALOG ────────────────────────────────────
        elif action_type == "ADD_PRODUCT":
            name = str(payload.get("name") or "").strip()
            cost_price = to_float(payload.get("cost_price", 0.0))
            selling_price = to_float(payload.get("selling_price", 0.0))
            current_stock = to_int(payload.get("current_stock", 20))
            reorder_threshold = to_int(payload.get("reorder_threshold", 10))
            category = str(payload.get("category") or "General").strip()
            unit = str(payload.get("unit") or "units").strip()

            product_error = check_new_product(name, cost_price, selling_price)
            if product_error:
                return fail(product_error)
            if current_stock is None or current_stock < 0 or reorder_threshold is None or reorder_threshold < 0:
                return fail("Initial stock and reorder threshold must be whole numbers of 0 or more.")
            existing = await db.products.find_one({
                "merchant_id": m_id,
                "name": {"$regex": f"^{re.escape(name)}$", "$options": "i"},
            })
            if existing:
                return fail(f"'{name}' is already in your catalog.")

            p_id = f"prod-{m_id[:8]}-{uuid.uuid4().hex[:6]}"

            prod_doc = {
                "product_id": p_id,
                "merchant_id": m_id,
                "name": name,
                "category": category,
                "cost_price": cost_price,
                "selling_price": selling_price,
                "effective_selling_price": selling_price,
                "active_campaign_id": None,
                "current_stock": current_stock,
                "reorder_threshold": reorder_threshold,
                "unit": unit,
                "created_at": now,
                "updated_at": now,
                "is_synthetic": True,
            }
            await db.products.insert_one(prod_doc)

            if current_stock > 0:
                mov_doc = {
                    "movement_id": f"mov-{uuid.uuid4().hex[:10]}",
                    "merchant_id": m_id,
                    "product_id": p_id,
                    "product_name": name,
                    "adjustment_type": "AUDIT_CORRECTION",
                    "quantity_change": current_stock,
                    "stock_before": 0,
                    "stock_after": current_stock,
                    "notes": "Initial catalog intake via Copilot Agent",
                    "created_at": now,
                    "is_synthetic": True,
                }
                await db.inventory_movements.insert_one(mov_doc)

            return ActionConfirmationResponse(
                success=True,
                message=f"Product '{name}' added to catalog successfully with {current_stock} initial {unit}.",
                executed_action_type=action_type,
                result_data={"product_id": p_id, "name": name, "selling_price": selling_price}
            )

        # ── 3. CREATE PROMOTIONAL CAMPAIGN ───────────────────────────────────
        elif action_type == "CREATE_CAMPAIGN":
            title = str(payload.get("title") or "New Promotional Campaign").strip()
            target_product_ids = payload.get("target_product_ids") or []
            discount_pct = to_float(payload.get("discount_pct", 10.0))
            budget_allocated = to_float(payload.get("budget_allocated", 1000.0))
            goal = to_int(payload.get("target_redemptions_goal", 50))

            if not isinstance(target_product_ids, list) or not target_product_ids:
                return fail("Pick at least one product for the campaign.")
            discount_error = check_discount(discount_pct)
            if discount_error:
                return fail(discount_error)
            if budget_allocated is None or budget_allocated < 0:
                return fail("Budget must be a number of 0 or more.")
            if goal is None or goal < 1:
                goal = 50

            start_date = str(payload.get("start_date") or date.today().strftime("%Y-%m-%d"))
            end_date = str(payload.get("end_date") or (date.today() + timedelta(days=6)).strftime("%Y-%m-%d"))
            try:
                if date.fromisoformat(end_date) < date.fromisoformat(start_date):
                    return fail("Campaign end date must be on or after the start date.")
            except ValueError:
                return fail("Campaign dates must be in YYYY-MM-DD format.")

            # Validate every target product BEFORE writing anything, so a bad product
            # can't leave a half-created campaign behind.
            target_products = []
            for pid in target_product_ids:
                prod = await db.products.find_one({"merchant_id": m_id, "product_id": str(pid)})
                if not prod:
                    return fail(f"Product '{pid}' not found in your catalog.")
                cost_error = check_discount_vs_cost(prod, discount_pct)
                if cost_error:
                    return fail(cost_error)
                target_products.append(prod)

            camp_id = f"camp-{uuid.uuid4().hex[:8]}"

            camp_doc = {
                "campaign_id": camp_id,
                "merchant_id": m_id,
                "title": title,
                "campaign_type": payload.get("campaign_type", "DISCOUNT_OFFER"),
                "target_product_ids": [p["product_id"] for p in target_products],
                "discount_pct": discount_pct,
                "budget_allocated": budget_allocated,
                "start_date": start_date,
                "end_date": end_date,
                "target_redemptions_goal": goal,
                "status": "ACTIVE",
                "created_at": now,
                "is_synthetic": True,
            }
            await db.campaigns.insert_one(camp_doc)

            # Apply promotional discount to target products (already validated above)
            for prod in target_products:
                orig_sp = float(prod.get("selling_price", 0.0))
                discounted_price = round(orig_sp * (1.0 - (discount_pct / 100.0)), 2)
                await db.products.update_one(
                    {"merchant_id": m_id, "product_id": prod["product_id"]},
                    {"$set": {
                        "effective_selling_price": discounted_price,
                        "active_campaign_id": camp_id
                    }}
                )

            return ActionConfirmationResponse(
                success=True,
                message=f"Campaign '{title}' is now ACTIVE with {discount_pct:g}% discount on {len(target_products)} target item(s).",
                executed_action_type=action_type,
                result_data={"campaign_id": camp_id, "status": "ACTIVE"}
            )

        # ── 4. END ACTIVE PROMOTIONAL CAMPAIGN ──────────────────────────────
        elif action_type == "END_CAMPAIGN":
            camp_id = payload.get("campaign_id")
            camp = await db.campaigns.find_one({"merchant_id": m_id, "campaign_id": camp_id})
            if not camp:
                return ActionConfirmationResponse(
                    success=False,
                    message=f"Campaign '{camp_id}' not found.",
                    executed_action_type=action_type
                )

            # Mark COMPLETED
            await db.campaigns.update_one(
                {"merchant_id": m_id, "campaign_id": camp_id},
                {"$set": {"status": "COMPLETED"}}
            )

            # Revert targeted products to regular retail price
            if camp.get("target_product_ids"):
                for pid in camp["target_product_ids"]:
                    prod = await db.products.find_one({"merchant_id": m_id, "product_id": pid})
                    if prod:
                        orig_sp = float(prod.get("selling_price", 0.0))
                        await db.products.update_one(
                            {"merchant_id": m_id, "product_id": pid},
                            {"$set": {
                                "effective_selling_price": orig_sp,
                                "active_campaign_id": None
                            }}
                        )

            return ActionConfirmationResponse(
                success=True,
                message=f"Campaign '{camp.get('title')}' successfully ended. Regular catalog pricing restored.",
                executed_action_type=action_type,
                result_data={"campaign_id": camp_id, "status": "COMPLETED"}
            )

        else:
            return ActionConfirmationResponse(
                success=False,
                message=f"Unsupported action type '{action_type}'.",
                executed_action_type=action_type
            )


copilot_service = CopilotService()
