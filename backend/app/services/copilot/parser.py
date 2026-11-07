"""
Agent Intent Parser and Router for LocalPulse AI Copilot.
Bridges natural language to discrete tools using external LLM Function Calling (Gemini/OpenAI)
with a deterministic keyword fallback parser.
"""

import asyncio
import json
import logging
import re
from typing import Dict, Any, Optional, Tuple, List
import httpx
from app.core.config import settings
from app.services.copilot.tools import COPILOT_TOOLS
from app.services.time_periods import parse_period

logger = logging.getLogger(__name__)

# Words that signal a question about sales / money
SALES_WORDS = re.compile(
    r"\b(sales?|sold|sell|selling|sells|seller|sellers|revenue|earn\w*|made|income|turnover|"
    r"profits?|margins?|money|orders?|demand)\b"
)
# Ranking words: best / most ...
RANK_TOP = re.compile(r"\b(most|top|best|highest|biggest|popular|fastest|leading|maximum)\b|best[- ]?sell")
# ... and worst / least / not selling
RANK_BOTTOM = re.compile(
    r"\b(least|lowest|worst|bottom|slowest|weakest|poorest|minimum)\b"
    r"|\b(not|isn'?t|aren'?t|didn'?t|never|no)\s+(selling|sold|sell|sales)\b|\bzero\s+sales\b"
)
PRODUCT_WORDS = re.compile(r"\b(products?|items?|skus?|sellers?|performers?|things|goods|lines?)\b")
CHART_WORDS = re.compile(r"\b(chart|charts|graph|graphs|plot|visuali[sz]e|bar chart)\b")
ANALYZE_WORDS = re.compile(r"\b(analy[sz]e|analysis|performance|velocity|trend)\b|\bhow\s+(is|are|was|did|does)\b")


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
        # 0. "yes" / "show chart" right after an answer that has a chart -> show that chart.
        #    Checked before the LLM so a short "yes" is never misread as a new request.
        if self._is_chart_followup(query, history):
            return "show_chart", {}

        # 1. Try external LLM if configured
        if settings.LLM_API_KEY and settings.LLM_API_KEY.strip():
            try:
                provider = (settings.LLM_PROVIDER or "gemini").lower()
                if provider == "gemini":
                    tool, args = await self._parse_with_gemini(query, products, campaigns, history)
                else:
                    tool, args = await self._parse_with_openai_compatible(query, products, campaigns, history)
                if tool:
                    return tool, args
                # The LLM chose no tool: give the keyword router a chance before giving up.
                return self._parse_deterministic(query, products, campaigns, history)
            except Exception as e:
                from app.core.llm_monitor import is_gemini_rate_limit_error, record_gemini_rate_limit
                if is_gemini_rate_limit_error(e):
                    record_gemini_rate_limit()
                logger.error(f"External LLM tool calling failed ({e}). Reverting to rule-based parser.")

        # 2. Rule-based / Deterministic parser fallback with chat memory
        return self._parse_deterministic(query, products, campaigns, history)

    # Words that describe the action, not the product; ignored when matching product names.
    _MATCH_STOPWORDS = {
        "the", "and", "for", "with", "this", "that", "from", "into", "some", "more", "all",
        "restock", "replenish", "stock", "adjust", "increase", "add", "units", "unit", "packs",
        "pack", "bottles", "items", "item", "cartons", "boxes", "pieces", "pcs",
        "analyze", "analyse", "analysis", "performance", "velocity", "sales", "sale", "sold",
        "how", "did", "doing", "last", "days", "day", "week", "weeks", "month",
        "create", "launch", "draft", "campaign", "promotion", "offer", "discount", "special",
        "weekend", "off", "on", "of", "my", "our", "please", "can", "you", "what", "which",
        "suggest", "suggests", "suggested", "suggesting", "suggestion", "suggestions",
        "recommend", "recommends", "recommended", "recommending", "recommendation", "recommendations",
        "propose", "proposes", "proposed", "proposing", "proposal", "proposals",
        "start", "starts", "starting", "started", "begin", "begins", "setup",
        "improve", "improves", "improving", "improved", "improvement", "boost", "boosting",
        "grow", "grows", "growth", "growing", "increase", "increasing", "maximize", "optimize",
        "productivity", "produtivity", "profitability", "profitable",
        "candidate", "one", "two", "some", "best", "good", "idea", "ideas", "strategy", "push",
        "plan", "plans", "planning", "run", "runs", "running", "help", "need", "needs", "want", "wants",
        "like", "should", "could", "would", "first", "next",
        # question / analytics words that must never count as part of a product name
        "are", "was", "were", "is", "most", "top", "best", "worst", "least", "highest", "lowest",
        "selling", "sell", "sells", "seller", "sellers", "revenue", "profit", "profits", "money",
        "earn", "earned", "earning", "earnings", "made", "much", "many", "total", "show", "give",
        "tell", "list", "products", "product", "store", "shop", "business", "today", "yesterday",
        "compare", "comparison", "versus", "between", "fast", "slow", "slowest", "fastest",
        "moving", "popular", "rank", "ranking", "performing", "performer", "performers", "not",
        "any", "every", "each", "per", "about", "there", "have", "has", "had", "been", "get",
        "see", "view", "report", "summary", "overview", "past", "previous", "recent", "current",
        "these", "those", "them", "than", "then", "also", "over", "during", "few", "low",
        "urgent", "level", "need", "needs", "running", "out", "orders", "order", "demand",
        "margin", "margins", "trend", "biggest", "maximum", "minimum", "weakest", "poorest",
        "bottom", "leading", "goods", "things", "lines", "zero", "never", "isn", "aren", "didn",
        "months", "trends", "full", "health", "promotional", "active", "end", "stop", "run",
        "chart", "charts", "graph", "graphs", "plot", "visualize", "visualise", "bar", "then",
        "more", "better", "higher", "both", "side", "form", "want", "see", "yes", "yeah", "sure",
        "make", "display", "draw", "visual", "diagram", "instead", "now", "okay",
    }

    @staticmethod
    def _word_variants(word: str) -> set:
        """A word plus its simple singular form ("breads" -> {"breads", "bread"})."""
        variants = {word}
        if len(word) > 3 and word.endswith("es"):
            variants.add(word[:-2])
        if len(word) > 3 and word.endswith("s"):
            variants.add(word[:-1])
        return variants

    def _match_product_in_text(self, text: str, products: List[dict]) -> Optional[str]:
        """
        Find the catalog product whose name shares the most words with the text.
        Returns None when nothing matches or when two products tie (ambiguous),
        so the copilot asks which product instead of guessing.
        """
        if not text or not products:
            return None

        lowered = text.lower()
        # A full product name typed out always wins.
        for p in products:
            name = p.get("name", "").lower()
            if name and name in lowered:
                return p.get("name")

        query_words = set()
        for w in re.findall(r"[a-z]+", lowered):
            if len(w) >= 3 and w not in self._MATCH_STOPWORDS:
                query_words |= self._word_variants(w)
        if not query_words:
            return None

        best_name, best_score, tie = None, 0, False
        for p in products:
            name_words = set()
            for w in re.findall(r"[a-z]+", p.get("name", "").lower()):
                name_words |= self._word_variants(w)
            score = len(query_words & name_words)
            if score > best_score:
                best_name, best_score, tie = p.get("name"), score, False
            elif score == best_score and score > 0:
                tie = True

        if best_score == 0 or tie:
            return None
        return best_name

    def _is_chart_followup(self, query: str, history: Optional[List[dict]]) -> bool:
        """
        True when the merchant says yes / asks for the chart of the previous answer:
        "yes", "sure", "show chart", "show it as a graph", "haan".
        Only if the latest copilot reply actually has a chart.
        """
        if not history:
            return False
        last_assistant = next((m for m in reversed(history) if m.get("role") == "assistant"), None)
        if not last_assistant or not last_assistant.get("chart"):
            return False
        q = (query or "").lower().strip()
        if re.fullmatch(r"(yes|yeah|yep|yup|sure|ok|okay|y|haan|ha|han|please|yes please|ok show|go ahead)[.! ]*", q):
            return True
        # Chart words and nothing else meaningful ("show chart", "make it a graph", "as a chart please")
        return bool(CHART_WORDS.search(q)) and not self._has_unmatched_words(q) and not SALES_WORDS.search(q)

    def _match_all_products_in_text(self, text: str, products: List[dict]) -> List[str]:
        """
        Every product named anywhere in the sentence, in the order mentioned, however they
        are joined: "compare milk and rice", "analyze atta then analyze tea", "milk vs oil".
        A word counts only if it points to exactly one product (an ambiguous word like "oil"
        in a shop selling two oils is ignored unless another word, e.g. "sunflower", decides).
        """
        lowered = (text or "").lower()
        found: Dict[str, int] = {}  # product name -> position of first mention

        # Full product names typed out
        for p in products:
            name = p.get("name", "")
            pos = lowered.find(name.lower()) if name else -1
            if pos >= 0:
                found.setdefault(name, pos)

        name_words = {
            p.get("name", ""): set().union(*(self._word_variants(w) for w in re.findall(r"[a-z]+", p.get("name", "").lower())))
            for p in products if p.get("name")
        }
        for m in re.finditer(r"[a-z]+", lowered):
            w = m.group(0)
            if len(w) < 3 or w in self._MATCH_STOPWORDS:
                continue
            variants = self._word_variants(w)
            hits = [name for name, words in name_words.items() if variants & words]
            if len(hits) == 1:
                found.setdefault(hits[0], m.start())

        return [name for name, _ in sorted(found.items(), key=lambda kv: kv[1])]

    def _has_unmatched_words(self, text: str) -> bool:
        """True if the text has content words that aren't action words (e.g. an unknown product name)."""
        return any(
            len(w) >= 3 and w not in self._MATCH_STOPWORDS
            for w in re.findall(r"[a-z]+", text.lower())
        )

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

        client = genai.Client(
            api_key=settings.LLM_API_KEY
        )
        raw_model = (settings.LLM_MODEL or "gemini-3.5-flash-lite").strip().lower()
        if "3.5-flash-lite" in raw_model:
            model_name = "gemini-3.5-flash-lite"
        elif "3.5" in raw_model:
            model_name = "gemini-3.5-flash"
        elif "3.8" in raw_model:
            model_name = "gemini-3.8-flash"
        elif "flash-lite" in raw_model:
            model_name = "gemini-3.5-flash-lite"
        elif "pro" in raw_model:
            model_name = "gemini-2.5-pro"
        elif "1.5" in raw_model or "2.0" in raw_model or "2.5" in raw_model:
            model_name = "gemini-3.5-flash-lite"
        else:
            model_name = raw_model

        system_instruction = (
            "You are an AI Business Copilot Agent for an Indian MSME merchant. "
            "Given the user's message and recent chat history, select the most appropriate operational tool. "
            "Extract parameters carefully. If the user refers to previous items (e.g. 'restock it', 'discount this'), "
            "resolve the product from the conversation history. "
            "For listing catalog products or viewing all inventory items use get_catalog_products; "
            "for rankings across products (most sold, best sellers, not selling) use get_top_products; "
            "for store totals (how much did I sell, revenue yesterday, profit this month) use get_sales_summary; "
            "for comparing named products use compare_products; "
            "for neighborhood spatial maps and finding nearby stores use get_nearby_merchants; "
            "for local festivals, holidays, and occasions calendar use get_upcoming_events; "
            "for festival readiness and occasion action plans use get_event_action_plan; "
            "for partner cross-store bundle suggestions use discover_collaboration_partners; "
            "for drafting or proposing joint bundles to a neighbor use create_collaboration_proposal; "
            "for forward-looking demand forecasting and stockout risks use get_demand_forecast. "
            "Whenever the merchant mentions a time period, pass it in the 'period' argument exactly as they said it."
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

        fn_declarations = []
        for t in COPILOT_TOOLS:
            fn_declarations.append({
                "name": t["name"],
                "description": t["description"],
                "parameters": t["parameters"]
            })

        try:
            response = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=genai_types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.1,
                        tools=[genai_types.Tool(function_declarations=fn_declarations)] 
                    )
                ),
                timeout=15.0
            )
        except Exception as e:
            from app.core.llm_monitor import is_gemini_rate_limit_error, record_gemini_rate_limit
            if is_gemini_rate_limit_error(e):
                record_gemini_rate_limit()
            logger.warning(f"External LLM generate_content call timed out or failed ({e}). Reverting to rule-based parser.")
            return None, {}

        if response.candidates:
            for part in response.candidates[0].content.parts:
                if hasattr(part, "function_call") and part.function_call:
                    fn_name = part.function_call.name
                    fn_args = dict(part.function_call.args or {})
                    return fn_name, fn_args

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
            "Resolve contextual references (it, this, that, etc.) from recent conversation turns. "
            "For rankings across products use get_top_products; for store totals use get_sales_summary; "
            "for comparing named products use compare_products; "
            "for neighborhood spatial maps and nearby shops use get_nearby_merchants; "
            "for festivals, holidays, and event calendar use get_upcoming_events; "
            "for festival readiness action plans use get_event_action_plan; "
            "for cross-store combo and bundle discovery use discover_collaboration_partners; "
            "for sending joint bundle proposals use create_collaboration_proposal; "
            "for forward-looking demand forecasting and stockout risks use get_demand_forecast. "
            "Whenever the merchant mentions a time period, pass it in the 'period' argument exactly as they said it."
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
            matched = self._match_product_in_text(q, products)
            if matched:
                return matched
            if history and re.search(r"\b(it|this|that|same|them|those)\b", q):
                return self._find_recent_product_in_history(history, products)
            return None

        # 1. Add product intent: "add product [name] cost [x] selling [y]" or "add 30 units of Almond Milk price 90 cost 60"
        if (
            any(w in q for w in ["add product", "create product", "new product", "add sku", "add item", "new sku", "new item"])
            or (re.search(r'\badd\b', q) and re.search(r'\b(?:cost|selling|price|cp|sp)\b', q))
        ):
            name_match = (
                re.search(r'(?:add\s+product|new\s+product|add\s+item|create\s+product|add\s+sku)\s+([a-zA-Z0-9\s]+?)(?:cost|selling|price|category|stock|units?|with|$)', q)
                or re.search(r'\badd\b\s*(?:\d+\s*(?:units?|packs?|pcs|bottles?|items?)?\s*(?:of\s*)?)?([a-zA-Z0-9\s]+?)(?:cost|selling|price|category|stock|units?|with|$)', q)
            )
            name = name_match.group(1).strip() if name_match else "New Catalog Item"
            name = re.sub(r'^(a|an|the)\s+', '', name, flags=re.I).strip()

            cost_m = (
                re.search(r'(?:cost|cost\s*price|cp|bought\s*at|buy\s*at|wholesale|purchase)\s*[:=]?\s*(?:₹|rs\.?)?\s*(\d+(?:\.\d+)?)', q)
                or re.search(r'(?:₹|rs\.?)?\s*(\d+(?:\.\d+)?)\s*(?:cost|cp)', q)
            )
            sell_m = (
                re.search(r'(?:selling|selling\s*price|sp|sell\s*at|price|retail|mrp)\s*[:=]?\s*(?:₹|rs\.?)?\s*(\d+(?:\.\d+)?)', q)
                or re.search(r'(?:₹|rs\.?)?\s*(\d+(?:\.\d+)?)\s*(?:selling|price|sp|retail)', q)
            )
            stock_m = (
                re.search(r'(?:stock|initial\s*stock|qty|quantity)\s*[:=]?\s*(\d+)', q)
                or re.search(r'(\d+)\s*(?:units?|packs?|bottles?|items?|pieces?|pcs|kg|litres?)', q)
            )

            all_numbers = [float(n) for n in re.findall(r'\b\d+(?:\.\d+)?\b', q)]
            cost_price = float(cost_m.group(1)) if cost_m else None
            selling_price = float(sell_m.group(1)) if sell_m else None
            stock = int(stock_m.group(1)) if stock_m else None

            remaining_nums = [n for n in all_numbers if n != stock and n != cost_price and n != selling_price]
            if cost_price is None and selling_price is None:
                if len(remaining_nums) >= 2:
                    lower = min(remaining_nums[0], remaining_nums[1])
                    higher = max(remaining_nums[0], remaining_nums[1])
                    cost_price, selling_price = lower, higher
                elif len(remaining_nums) == 1:
                    cost_price = remaining_nums[0]
                    selling_price = round(cost_price * 1.3, 2)
            elif cost_price is None and selling_price is not None:
                cost_price = round(remaining_nums[0] if remaining_nums else selling_price * 0.75, 2)
            elif selling_price is None and cost_price is not None:
                selling_price = round(remaining_nums[0] if remaining_nums else cost_price * 1.3, 2)

            cost_price = cost_price or 50.0
            selling_price = selling_price or (cost_price * 1.3)
            stock = stock if stock is not None else (int(remaining_nums[0]) if remaining_nums else 25)

            cat = "General"
            for cat_candidate in [
                "dairy", "bakery", "beverage", "grocery", "snacks", "personal care",
                "household", "sweets", "produce", "fruits", "vegetables", "spices",
                "staples", "packaged food", "cleaning", "pharmacy"
            ]:
                if cat_candidate in q:
                    cat = cat_candidate.title()
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
        if re.search(r"\b(end|stop|cancel|conclude|finish|close|terminate)\b.*\b(campaigns?|promotions?|offers?|promos?)\b", q):
            matched_title = ""
            for c in campaigns:
                if c.get("title") and c.get("title", "").lower() in q:
                    matched_title = c.get("title")
                    break
            return "end_promotional_campaign", {
                "campaign_title_or_id": matched_title
            }

        # 3. Create campaign / discount promotion / suggest campaign to start
        if (
            re.search(r'\b(create|launch|draft|start|run|new|suggest|recommend|propose|plan|give|need|want)\b.*\b(campaigns?|promotions?|offers?|promos?)\b', q)
            or re.search(r'\b(campaigns?|promotions?|offers?|promos?)\b.*\b(start|run|launch|create|begin|setup|recommend|suggest|idea|ideas|improve)\b', q)
            or any(w in q for w in [
                "create campaign", "launch campaign", "draft campaign", "draft promotion",
                "weekend offer", "weekend special", "discount campaign", "start campaign",
                "run campaign", "new campaign", "promotion for", "offer on", "offer for",
                "campaign to start", "campaign to run", "suggest campaign", "recommend campaign",
                "suggest a campaign", "recommend a campaign", "suggest one campaign", "recommend one campaign",
                "campaign idea", "campaign ideas", "best campaign", "which campaign"
            ])
            or re.search(r"\d+(?:\.\d+)?\s*%\s*(?:off|discount)", q)
        ):
            pct_match = re.search(r'(\d+(?:\.\d+)?)\s*%', q) or re.search(r'(\d+(?:\.\d+)?)\s*percent', q)
            pct = float(pct_match.group(1)) if pct_match else 10.0

            dur_m = re.search(r'(?:for|duration|over)\s*(\d+)\s*days?', q) or re.search(r'\b(\d+)\s*days?\s*(?:offer|campaign|promo)?\b', q)
            dur_w = re.search(r'\b(\d+)\s*weeks?\b', q)
            duration_days = int(dur_m.group(1)) if dur_m else (int(dur_w.group(1)) * 7 if dur_w else 7)

            bud_m = (
                re.search(r'(?:budget|spend|cost|allocat\w*)\s*(?:of|is|[:=])?\s*(?:₹|rs\.?)?\s*(\d+(?:\.\d+)?)', q)
                or re.search(r'(?:₹|rs\.?)?\s*(\d+(?:\.\d+)?)\s*(?:budget|spend)', q)
            )
            budget = float(bud_m.group(1)) if bud_m else 1000.0

            target_p = resolve_target_product()

            title = f"Special Offer: {target_p or 'Store Favorites'}"
            if not target_p:
                if any(k in q for k in ["productivity", "produtivity", "profit", "margin", "grow", "boost", "improve"]):
                    title = "Productivity Lift: High-Margin Value Push"
                elif any(k in q for k in ["weekend", "saturday", "sunday"]):
                    title = "Weekend Special: Store Favorites"
            for occ in ["diwali", "holi", "eid", "pongal", "christmas", "new year", "weekend", "monsoon", "summer"]:
                if occ in q:
                    title = f"{occ.title()} Special: {target_p or 'Store Favorites'}"
                    break

            args = {
                "title": title,
                "product_name": target_p or "",
                "discount_pct": pct,
                "duration_days": duration_days,
                "budget": budget
            }
            if not target_p and (not self._has_unmatched_words(q) or any(w in q for w in ["suggest", "recommend", "best", "favorite", "productivity", "produtivity", "grow", "boost", "idea", "any", "start", "improve"])):
                args["auto_select"] = "best_promo_candidate"
            return "create_promotional_campaign", args

        # 4. Restock / Adjust stock / Damage loss intent
        if any(w in q for w in ["restock", "adjust stock", "replenish", "add stock", "increase stock", "damage", "loss", "spoiled", "expired", "broken", "deduct stock", "remove stock"]):
            is_damage = any(w in q for w in ["damage", "damaged", "loss", "waste", "spoiled", "expired", "broken", "defect", "leakage", "deduct", "remove", "reduce"])
            is_audit = any(w in q for w in ["audit", "correction", "count mismatch", "inventory check", "physical count"])
            adj_type = "DAMAGE_LOSS" if is_damage else ("AUDIT_CORRECTION" if is_audit else "RESTOCK")

            qty_match = (
                re.search(r'(?:\bby|\badd|\bwith|\+|\bdeduct|\bremove|\blost|\bdamaged)\s*(\d+)\b', q)
                or re.search(r'\b(\d+)\s*(?:units?|packs?|bottles?|items?|cartons?|boxes?|pcs|pieces)\b', q)
                or re.search(r'(?<![\w.])(\d+)(?![\w.%])', q)
            )
            qty = int(qty_match.group(1)) if qty_match else (5 if is_damage else 25)

            is_inquiry = (
                re.search(r'\b(which|who|what)\b', q) is not None
                and re.search(r'\b(by|with|add|deduct|remove)\b', q) is None
            )

            target_p = resolve_target_product()

            if is_inquiry and not target_p and adj_type == "RESTOCK":
                return "get_restock_recommendations", {}

            notes = (
                f"Recorded as {adj_type.replace('_', ' ').title()} via Copilot"
                if is_damage or is_audit
                else f"Replenished via Copilot replenishment request (Context: {target_p or 'lead'})"
            )

            args = {
                "product_name": target_p or "",
                "quantity": qty,
                "adjustment_type": adj_type,
                "notes": notes
            }
            if not target_p and re.search(r"\b(top|most|lowest|urgent|critical|low|neediest)\b", q) and adj_type == "RESTOCK":
                args["auto_select"] = "most_urgent_restock"
            return "adjust_inventory_stock", args

        # 4b. Demand Forecasting intent
        if any(w in q for w in ["forecast", "projected demand", "demand forecast", "future demand", "predict sales", "sales projection", "forecasted"]):
            target_p = resolve_target_product()
            days_m = re.search(r'\b(\d+)\s*(?:days?|day)\b', q)
            days = int(days_m.group(1)) if days_m else 7
            return "get_demand_forecast", {
                "product_name": target_p or ("all" if "all" in q or "store" in q or "everything" in q else ""),
                "days": min(14, max(1, days))
            }

        # 4c. Event Action Plan intent
        if any(w in q for w in ["action plan", "prepare for", "prep for", "plan for", "readiness plan"]) and any(w in q for w in ["diwali", "holi", "eid", "pongal", "christmas", "festival", "occasion", "event", "ipl", "new year"]):
            occ_m = re.search(r'(?:action plan for|prepare for|prep for|plan for|readiness plan for)\s+([a-zA-Z\s]+)', q)
            occ_name = occ_m.group(1).strip() if occ_m else "Festival"
            return "get_event_action_plan", {"occasion_name": occ_name}

        # 4d. Upcoming Events / Festival Calendar
        if any(w in q for w in ["festival", "festivals", "upcoming event", "upcoming events", "occasions", "holiday", "holidays", "calendar", "what's happening"]):
            days_m = re.search(r'\b(\d+)\s*days?\b', q)
            days = int(days_m.group(1)) if days_m else (60 if "next month" in q or "2 months" in q else 30)
            return "get_upcoming_events", {"days": days}

        # 4e. Create Collaboration Proposal
        if any(w in q for w in [
            "propose bundle", "propose a bundle", "propose combo", "propose a combo",
            "propose a joint", "propose joint", "send proposal", "draft proposal",
            "collab proposal", "partner proposal", "create proposal", "send collab",
            "joint combo bundle with", "joint bundle with", "bundle proposal"
        ]):
            partner_m = re.search(r'(?:to|with|for)\s+([a-zA-Z0-9\s\']+?)(?:on|with|for|at|combo|bundle|$)', q)
            partner_name = partner_m.group(1).strip() if partner_m else ""
            target_p = resolve_target_product()
            return "create_collaboration_proposal", {
                "partner_name": partner_name,
                "my_product_name": target_p or "",
                "discount_pct": 10.0,
            }

        # 4f. Discover Collaboration Partners
        if any(w in q for w in ["collaborat", "bundle partner", "bundle partners", "partner shop", "partner stores", "joint bundle", "joint combo", "synergy partner", "cross-store"]):
            target_p = resolve_target_product()
            return "discover_collaboration_partners", {"product_name": target_p or ""}

        # 4g. Neighborhood Map & Nearby Stores
        if any(w in q for w in ["nearby", "near me", "closest store", "closest shop", "neighboring", "around me", "stores near", "shops near", "map", "neighborhood footprint"]):
            rad_m = re.search(r'(?:within|in|radius\s*of)?\s*(\d+(?:\.\d+)?)\s*(?:km|kms|kilometers?)', q)
            radius_km = float(rad_m.group(1)) if rad_m else None
            cat = None
            for cat_c in ["bakery", "dairy", "cafe", "grocery", "pharmacy", "sweets", "fashion"]:
                if cat_c in q:
                    cat = cat_c.title()
                    break
            return "get_nearby_merchants", {
                "radius_km": radius_km,
                "category": cat or "",
                "limit": 5
            }

        # 5. List / Show all products in catalog
        if (
            re.search(r'\b(list|show|view|tell|see)\b.*\b(?:all\s+)?(?:the\s+)?(products?|items?|catalog|skus?|inventory)\b', q)
            or re.search(r'\bwhat\s+(?:products?|items?)\s+(?:do\s+i\s+have|are\s+there|in\s+stock)\b', q)
            or q in ["all products", "list products", "show products", "show catalog", "list catalog", "inventory list"]
        ) and not any(w in q for w in ["add", "restock", "damage", "loss", "forecast", "compare", "campaign", "offer"]):
            cat_candidate = None
            for cat_c in ["dairy", "flour", "grains", "edible oils", "oils", "spices", "beverages", "tea", "salt"]:
                if cat_c in q:
                    cat_candidate = cat_c
                    break
            return "get_catalog_products", {"category": cat_candidate or ""}

        # 6. Restock recommendation inquiry
        if any(w in q for w in ["low stock", "reorder threshold", "depleted", "shortage", "out of stock", "running low"]):
            return "get_restock_recommendations", {}

        # 7. Discount recommendations for surplus stock
        if any(w in q for w in ["recommended discount", "clearance", "dead stock", "slow moving", "surplus", "discount strategy"]):
            return "get_discount_recommendations", {"max_discount_pct": 15.0}

        period_phrase = query
        has_sales_words = SALES_WORDS.search(q) is not None
        is_overview = re.search(r"\b(overview|snapshot|health|status)\b", q) is not None

        # 7. Compare named products
        if re.search(r"\bcompare\b|\bcomparison\b|\bvs\.?\b|\bversus\b", q):
            return "compare_products", {
                "product_names": self._match_all_products_in_text(q, products),
                "period": period_phrase,
            }

        # 7b. Two or more products named in a sales/analysis question -> compare them
        named = self._match_all_products_in_text(q, products)
        if len(named) >= 2 and (has_sales_words or ANALYZE_WORDS.search(q) or CHART_WORDS.search(q)
                                or re.search(r"\b(more|better|higher)\b", q)):
            return "compare_products", {"product_names": named, "period": period_phrase}

        # 8. Rankings across products
        is_top = RANK_TOP.search(q) is not None
        is_bottom = RANK_BOTTOM.search(q) is not None
        if (is_top or is_bottom) and (has_sales_words or PRODUCT_WORDS.search(q)):
            if ANALYZE_WORDS.search(q) and re.search(r"\b(top|best)[- ](product|item|seller|selling)\b", q) \
                    and not re.search(r"\b(products|items|sellers)\b", q):
                return "analyze_product_performance", {"auto_select": "top_seller", "period": period_phrase}

            if re.search(r"\b(revenue|money|earn\w*|income|rupees?|turnover|value)\b|₹", q):
                rank_by = "revenue"
            elif re.search(r"\b(profit|profits|profitable|margins?)\b", q):
                rank_by = "profit"
            else:
                rank_by = "units"
            limit_m = (
                re.search(r"\b(?:top|bottom|best|worst|least|lowest)\s+(\d{1,2})\b", q)
                or re.search(r"\b(\d{1,2})\s+(?:best|top|most|least|worst|slowest|highest|lowest)\b", q)
            )
            args = {
                "period": period_phrase,
                "rank_by": rank_by,
                "order": "bottom" if is_bottom else "top",
            }
            if limit_m:
                args["limit"] = int(limit_m.group(1))
            return "get_top_products", args

        # 9. One named product + a sales/performance question
        target_p = self._match_product_in_text(q, products)
        if target_p and (has_sales_words or ANALYZE_WORDS.search(q)):
            return "analyze_product_performance", {"product_name": target_p, "period": period_phrase}

        # 10. Analyze / performance wording
        if ANALYZE_WORDS.search(q) or "sales of" in q:
            target_p = resolve_target_product()
            if target_p:
                return "analyze_product_performance", {"product_name": target_p, "period": period_phrase}
            if not is_overview:
                return "get_sales_summary", {"period": period_phrase}

        # 11. Store-wide sales totals
        if not is_overview and (
            has_sales_words
            or re.search(r"\bhow\s+(?:much|many)\b", q)
            or re.search(r"\bsales?\s+summary\b", q)
        ):
            return "get_sales_summary", {"period": period_phrase}

        # 12. Store overview / business snapshot / productivity suggestions
        overview_patterns = [
            r'\boverview\b', r'\bsummary\b', r'\bsnapshot\b', r'\bstatus\b',
            r'\bhealth\b', r'\bhello\b', r'\bhi\b', r'\bhelp\b',
            r'\bpro?ductiv\w*\b', r'\brecommend\w*\b', r'\bsuggest\w*\b',
            r'\btips?\b', r'\b(?:how\s+to\s+)?improve\b', r'\badvice\b',
            r'\bboost\s+(?:sales|business|profit|margin)\b',
            r'\bgrowth\s+(?:tips|advice|strategy|plan)\b'
        ]
        if any(re.search(pat, q) for pat in overview_patterns):
            return "get_business_overview", {}

        # 13. Only a time period ("how was yesterday?", "this week?") -> sales summary
        if parse_period(q).explicit and not self._has_unmatched_words(q):
            return "get_sales_summary", {"period": period_phrase}

        # 14. Could not be mapped to any store tool
        return None, {}


agent_tool_parser = AgentToolParser()
