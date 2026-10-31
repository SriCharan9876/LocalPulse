"""
Agent Intent Parser and Router for LocalPulse AI Copilot.
Bridges natural language to discrete tools using external LLM Function Calling (Gemini/OpenAI)
with a deterministic keyword fallback parser.
"""

import json
import logging
import re
from typing import Dict, Any, Optional, Tuple, List
import httpx
from app.core.config import settings
from app.services.copilot_tools import COPILOT_TOOLS

logger = logging.getLogger(__name__)

class AgentToolParser:
    """Parses user requests into tool calls using LLMs or deterministic heuristic parser."""

    async def parse_intent(
        self,
        query: str,
        products: List[dict],
        campaigns: List[dict],
        history: Optional[List[dict]] = None
    ) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Returns (tool_name, tool_args).
        If tool cannot be mapped, tool_name is None.
        Incorporates recent conversation history to resolve referential intents.
        """
        # 1. Try external LLM if configured
        if settings.LLM_API_KEY and settings.LLM_API_KEY.strip():
            try:
                provider = (settings.LLM_PROVIDER or "gemini").lower()
                if provider == "gemini":
                    return await self._parse_with_gemini(query, products, campaigns, history)
                else:
                    return await self._parse_with_openai_compatible(query, products, campaigns, history)
            except Exception as e:
                logger.error(f"External LLM tool calling failed ({e}). Reverting to rule-based parser.")

        # 2. Rule-based / Deterministic parser fallback with chat memory
        return self._parse_deterministic(query, products, campaigns, history)

    def _find_recent_product_in_history(
        self,
        history: Optional[List[dict]],
        products: List[dict]
    ) -> Optional[str]:
        """
        Inspects recent conversation turns (latest to oldest) to discover what product
        was most recently discussed, analyzed, or proposed.
        """
        if not history or not products:
            return None

        for msg in reversed(history):
            # Check draft_action payload first
            draft = msg.get("draft_action")
            if draft and isinstance(draft, dict):
                p_name = draft.get("payload", {}).get("product_name")
                if p_name:
                    return p_name
                p_id = draft.get("payload", {}).get("product_id")
                if p_id:
                    for p in products:
                        if p.get("product_id") == p_id:
                            return p.get("name")

            # Check message content for mention of catalog products
            content = (msg.get("content") or "").lower()
            for p in products:
                if p.get("name", "").lower() in content:
                    return p.get("name")

        return None

    async def _parse_with_gemini(
        self,
        query: str,
        products: List[dict],
        campaigns: List[dict],
        history: Optional[List[dict]] = None
    ) -> Tuple[Optional[str], Dict[str, Any]]:
        """Call Gemini with structured tool declarations and chat memory."""
        from google import genai
        from google.genai import types as genai_types

        client = genai.Client(api_key=settings.LLM_API_KEY)
        model_name = settings.LLM_MODEL or "gemini-1.5-flash"

        system_instruction = (
            "You are an AI Business Copilot Agent for an Indian MSME merchant. "
            "Given the user's message and recent chat history, select the most appropriate operational tool. "
            "Extract parameters carefully. If the user refers to previous items (e.g. 'restock it', 'discount this'), "
            "resolve the product from the conversation history."
        )

        history_context = ""
        if history:
            recent_turns = history[-5:]
            formatted_turns = []
            for m in recent_turns:
                role = "Merchant" if m.get("role") == "user" else "Copilot"
                txt = (m.get("content") or "").replace("\n", " ")[:200]
                formatted_turns.append(f"{role}: {txt}")
            history_context = "Recent Conversation Memory:\n" + "\n".join(formatted_turns) + "\n\n"

        prompt = (
            f"{history_context}"
            f"Active Catalog Items: {[p.get('name') for p in products[:15]]}\n"
            f"Active Campaigns: {[c.get('title') for c in campaigns if c.get('status') == 'ACTIVE']}\n\n"
            f"User Query: {query}"
        )

        # Use JSON tool calling via structured generation or function declaration
        # Standard function calling format:
        fn_declarations = []
        for t in COPILOT_TOOLS:
            fn_declarations.append({
                "name": t["name"],
                "description": t["description"],
                "parameters": t["parameters"]
            })

        response = await client.aio.models.generate_content(
            model=model_name,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.1,
                tools=[{"function_declarations": fn_declarations}]
            )
        )

        # Check for function calls in response candidates
        if response.candidates:
            for part in response.candidates[0].content.parts:
                if hasattr(part, "function_call") and part.function_call:
                    fn_name = part.function_call.name
                    fn_args = dict(part.function_call.args or {})
                    return fn_name, fn_args

        # If LLM responded without any function call, it means intent cannot be mapped
        return None, {}

    async def _parse_with_openai_compatible(
        self,
        query: str,
        products: List[dict],
        campaigns: List[dict],
        history: Optional[List[dict]] = None
    ) -> Tuple[Optional[str], Dict[str, Any]]:
        """Call OpenAI or Groq with tools parameter and conversation history."""
        api_url = settings.LLM_BASE_URL or "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.LLM_API_KEY}",
            "Content-Type": "application/json",
        }
        
        tools_payload = [
            {"type": "function", "function": t} for t in COPILOT_TOOLS
        ]

        system_content = (
            "You are an AI Business Copilot Agent for an Indian MSME merchant. "
            "Select the matching operational tool if user intent clearly matches store operations. "
            "If user asks general knowledge or unrelated questions, call no tool. "
            "Resolve contextual references (it, this, that, etc.) from recent conversation turns."
        )

        messages = [
            {"role": "system", "content": system_content}
        ]

        if history:
            for m in history[-4:]:
                r = "user" if m.get("role") == "user" else "assistant"
                txt = (m.get("content") or "")[:250]
                messages.append({"role": r, "content": txt})

        messages.append({
            "role": "user",
            "content": f"Catalog: {[p.get('name') for p in products[:15]]}. Query: {query}"
        })

        body = {
            "model": settings.LLM_MODEL or "gpt-4o-mini",
            "messages": messages,
            "tools": tools_payload,
            "tool_choice": "auto",
            "temperature": 0.1,
        }

        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.post(api_url, json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            choice = data["choices"][0]["message"]
            if choice.get("tool_calls"):
                tc = choice["tool_calls"][0]["function"]
                fn_name = tc["name"]
                fn_args = json.loads(tc.get("arguments", "{}"))
                return fn_name, fn_args

        return self._parse_deterministic(query, products, campaigns, history)

    def _parse_deterministic(
        self,
        query: str,
        products: List[dict],
        campaigns: List[dict],
        history: Optional[List[dict]] = None
    ) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Deterministic intent parser with conversation memory.
        Resolves product references ("it", "this product", "that") from recent chat turns.
        """
        q = query.lower().strip()

        def resolve_target_product() -> Optional[str]:
            # Direct mention in query
            for p in products:
                if p.get("name", "").lower() in q:
                    return p.get("name")
            # If not explicitly named, check if recent history referenced a product
            if history:
                return self._find_recent_product_in_history(history, products)
            return None

        # 1. Add product intent: "add product [name] cost [x] selling [y]"
        if any(w in q for w in ["add product", "create product", "new product", "add sku", "add item"]):
            # Extract numbers if present
            numbers = [float(n) for n in re.findall(r'\b\d+(?:\.\d+)?\b', q)]
            # Extract name
            name_match = re.search(r'(?:add product|new product|add item|create product)\s+([a-zA-Z0-9\s]+?)(?:cost|selling|price|category|with|$)', q)
            name = name_match.group(1).strip() if name_match else "New Catalog Item"
            cost_price = numbers[0] if len(numbers) >= 1 else 50.0
            selling_price = numbers[1] if len(numbers) >= 2 else (cost_price * 1.3)
            stock = int(numbers[2]) if len(numbers) >= 3 else 25

            # Extract category keyword
            cat = "General"
            for cat_candidate in ["dairy", "bakery", "beverage", "grocery", "snacks"]:
                if cat_candidate in q:
                    cat = cat_candidate.capitalize()
                    break

            return "add_catalog_product", {
                "name": name.title(),
                "category": cat,
                "cost_price": cost_price,
                "selling_price": selling_price,
                "initial_stock": stock,
                "reorder_threshold": 10,
                "unit": "units"
            }

        # 2. End campaign intent
        if any(w in q for w in ["end campaign", "stop campaign", "cancel campaign", "conclude campaign", "finish campaign"]):
            # Try to match campaign title
            matched_title = ""
            for c in campaigns:
                if c.get("title", "").lower() in q:
                    matched_title = c.get("title")
                    break
            return "end_promotional_campaign", {
                "campaign_title_or_id": matched_title or q
            }

        # 3. Create campaign / discount promotion
        if any(w in q for w in ["create campaign", "launch campaign", "draft campaign", "draft promotion", "weekend offer", "weekend special", "discount campaign"]):
            # Extract discount %
            pct_match = re.search(r'(\d+)\s*%', q)
            pct = float(pct_match.group(1)) if pct_match else 10.0
            
            target_p = resolve_target_product()

            return "create_promotional_campaign", {
                "title": f"Weekend Special: {target_p or 'Store Favorites'}",
                "product_name": target_p or (products[0].get("name") if products else ""),
                "discount_pct": pct,
                "duration_days": 7,
                "budget": 1000.0
            }

        # 4. Restock / Adjust stock intent
        if any(w in q for w in ["restock", "adjust stock", "replenish", "add stock", "increase stock"]):
            # Check if specific quantity mentioned
            qty_match = re.search(r'(?:by|add|with|\+)?\s*(\d+)\s*(?:units|packs|bottles|items|cartons|boxes)?', q)
            qty = int(qty_match.group(1)) if qty_match else 25

            # Check if user specifically asks a question: "which products need restock"
            is_inquiry = any(w in q for w in ["which", "who", "what"]) and not any(w in q for w in ["by", "with", "add"])

            target_p = resolve_target_product()

            if is_inquiry and not any(p.get("name", "").lower() in q for p in products):
                return "get_restock_recommendations", {}

            return "adjust_inventory_stock", {
                "product_name": target_p or (products[0].get("name") if products else ""),
                "quantity": qty,
                "adjustment_type": "RESTOCK",
                "notes": f"Triggered via Copilot replenishment request (Context: {target_p or 'lead'})"
            }

        # 5. Restock recommendation inquiry
        if any(w in q for w in ["low stock", "reorder threshold", "depleted", "shortage", "out of stock", "running low"]):
            return "get_restock_recommendations", {}

        # 6. Discount recommendations for surplus stock
        if any(w in q for w in ["recommended discount", "clearance", "dead stock", "slow moving", "surplus", "discount strategy"]):
            return "get_discount_recommendations", {"max_discount_pct": 15.0}

        # 7. Analyze product performance over last X days
        if any(w in q for w in ["analyze", "analysis", "performance", "velocity", "sales of", "how did", "how is"]):
            # Extract days (e.g. 7, 14, 30)
            days_match = re.search(r'(\d+)\s*(?:days|day|d)', q)
            days = int(days_match.group(1)) if days_match else 7

            target_p = resolve_target_product()

            if target_p or products:
                return "analyze_product_performance", {
                    "product_name": target_p or products[0].get("name", ""),
                    "days": days
                }

        # 8. Store overview / business snapshot
        overview_patterns = [r'\boverview\b', r'\bsummary\b', r'\bsnapshot\b', r'\bstatus\b', r'\bhealth\b', r'\bhello\b', r'\bhi\b', r'\bhelp\b']
        if any(re.search(pat, q) for pat in overview_patterns):
            return "get_business_overview", {}

        # 9. Could not be mapped to any store tool
        return None, {}


agent_tool_parser = AgentToolParser()
