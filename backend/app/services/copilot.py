"""
LocalPulse AI Business Copilot Orchestration Service.
Agentic architecture: maps natural language to operational tools,
executes read analytics immediately, and creates audited DraftActions for store mutations.
"""

import logging
import uuid
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.schemas.copilot import (
    CopilotChatResponse, CopilotEvidenceItem, DraftAction,
    ActionConfirmationResponse
)
from app.services.copilot_parser import agent_tool_parser
from app.services.copilot_executor import copilot_tool_executor
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

        # Dispatch based on tool name
        if tool_name == "analyze_product_performance":
            return copilot_tool_executor.execute_analyze_product(
                args=tool_args,
                merchant=merchant,
                products=products,
                sales=recent_sales
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

        elif tool_name == "get_business_overview":
            return copilot_tool_executor.execute_get_business_overview(
                merchant=merchant,
                products=products,
                sales=recent_sales,
                campaigns=campaigns
            )

        else:
            # Query cannot be mapped to any operational tool
            return copilot_tool_executor.execute_unmapped_fallback(query=query)

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

        # ── 1. RESTOCK / ADJUST INVENTORY ────────────────────────────────────
        if action_type == "RESTOCK_INVENTORY":
            p_id = payload.get("product_id")
            qty = int(payload.get("quantity", 0))
            adj_type = payload.get("adjustment_type", "RESTOCK").upper()
            notes = payload.get("notes", "Replenished via AI Copilot confirmed draft")

            if qty <= 0:
                return ActionConfirmationResponse(
                    success=False,
                    message="Adjustment quantity must be greater than 0.",
                    executed_action_type=action_type
                )

            product = None
            if p_id:
                product = await db.products.find_one({"merchant_id": m_id, "product_id": p_id})
            
            # Fallback to name search if product_id was not found (or drafted with name)
            p_name = payload.get("product_name")
            if not product and p_name:
                product = await db.products.find_one({
                    "merchant_id": m_id,
                    "name": {"$regex": p_name.strip(), "$options": "i"}
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
            name = payload.get("name", "").strip()
            if not name:
                return ActionConfirmationResponse(
                    success=False,
                    message="Product name cannot be empty.",
                    executed_action_type=action_type
                )

            p_id = f"prod-{m_id[:8]}-{uuid.uuid4().hex[:6]}"
            cost_price = float(payload.get("cost_price", 0.0))
            selling_price = float(payload.get("selling_price", 0.0))
            current_stock = int(payload.get("current_stock", 20))
            reorder_threshold = int(payload.get("reorder_threshold", 10))
            category = payload.get("category", "General")
            unit = payload.get("unit", "units")

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
            title = payload.get("title", "New Promotional Campaign")
            camp_id = f"camp-{uuid.uuid4().hex[:8]}"
            target_product_ids = payload.get("target_product_ids", [])
            discount_pct = float(payload.get("discount_pct", 10.0))

            camp_doc = {
                "campaign_id": camp_id,
                "merchant_id": m_id,
                "title": title,
                "campaign_type": payload.get("campaign_type", "DISCOUNT_OFFER"),
                "target_product_ids": target_product_ids,
                "discount_pct": discount_pct,
                "budget_allocated": float(payload.get("budget_allocated", 1000.0)),
                "start_date": payload.get("start_date", date.today().strftime("%Y-%m-%d")),
                "end_date": payload.get("end_date", (date.today() + timedelta(days=7)).strftime("%Y-%m-%d")),
                "target_redemptions_goal": int(payload.get("target_redemptions_goal", 50)),
                "status": "ACTIVE",
                "created_at": now,
                "is_synthetic": True,
            }
            await db.campaigns.insert_one(camp_doc)

            # Apply promotional discount to target products
            if target_product_ids:
                for pid in target_product_ids:
                    prod = await db.products.find_one({"merchant_id": m_id, "product_id": pid})
                    if prod:
                        orig_sp = float(prod.get("selling_price", 0.0))
                        discounted_price = round(orig_sp * (1.0 - (discount_pct / 100.0)), 2)
                        await db.products.update_one(
                            {"merchant_id": m_id, "product_id": pid},
                            {"$set": {
                                "effective_selling_price": discounted_price,
                                "active_campaign_id": camp_id
                            }}
                        )

            return ActionConfirmationResponse(
                success=True,
                message=f"Campaign '{title}' is now ACTIVE with {discount_pct}% discount on {len(target_product_ids)} target item(s).",
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
