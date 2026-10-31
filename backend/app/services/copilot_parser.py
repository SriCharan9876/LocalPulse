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

        client = genai.Client(api_key=settings.LLM_API_KEY)
        model_name = settings.LLM_MODEL or "gemini-1.5-flash"

        system_instruction = (
            "You are an AI Business Copilot Agent for an Indian MSME merchant. "
            "Given the user's message and recent chat history, select the most appropriate operational tool. "
            "Extract parameters carefully. If the user refers to previous items (e.g. 'restock it', 'discount this'), "
            "resolve the product from the conversation history. "
            "For rankings across products (most sold, best sellers, not selling) use get_top_products; "
            "for store totals (how much did I sell, revenue yesterday, profit this month) use get_sales_summary; "
            "for comparing named products use compare_products. "
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
            "Resolve contextual references (it, this, that, etc.) from recent conversation turns. "
            "For rankings across products use get_top_products; for store totals use get_sales_summary; "
            "for comparing named products use compare_products. "
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
            # 1. Match on words in the query ("restock rice" -> "India Gate Basmati Rice ...").
            #    Previously this required the FULL catalog name to appear in the query.
            matched = self._match_product_in_text(q, products)
            if matched:
                return matched
            # 2. Only fall back to chat history when the merchant refers back to something
            #    ("restock it", "discount this"). Otherwise a product that isn't in the
            #    catalog (e.g. "bread" at a grocery) would silently resolve to an old one.
            if history and re.search(r"\b(it|this|that|same|them|those)\b", q):
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
        # Any wording like "end campaign", "end active promotional campaign", "stop the offer"
        if re.search(r"\b(end|stop|cancel|conclude|finish|close|terminate)\b.*\b(campaigns?|promotions?|offers?|promos?)\b", q):
            # Try to match campaign title
            matched_title = ""
            for c in campaigns:
                if c.get("title") and c.get("title", "").lower() in q:
                    matched_title = c.get("title")
                    break
            # Empty title -> the executor ends the only active campaign, or asks which one.
            return "end_promotional_campaign", {
                "campaign_title_or_id": matched_title
            }

        # 3. Create campaign / discount promotion
        if (
            any(w in q for w in ["create campaign", "launch campaign", "draft campaign", "draft promotion",
                                 "weekend offer", "weekend special", "discount campaign", "start campaign",
                                 "run campaign", "new campaign", "promotion for", "offer on", "offer for"])
            or re.search(r"\d+(?:\.\d+)?\s*%\s*(?:off|discount)", q)
        ):
            # Extract discount %
            pct_match = re.search(r'(\d+(?:\.\d+)?)\s*%', q)
            pct = float(pct_match.group(1)) if pct_match else 10.0

            target_p = resolve_target_product()
            args = {
                "title": f"Weekend Special: {target_p or 'Store Favorites'}",
                "product_name": target_p or "",
                "discount_pct": pct,
                "duration_days": 7,
                "budget": 1000.0
            }
            # No product mentioned at all ("Draft a weekend discount campaign with 12% off"):
            # let the executor pick the best candidate from stock and margins, and say why.
            # If an unknown product was mentioned ("... on bread"), leave it empty so it asks.
            if not target_p and not self._has_unmatched_words(q):
                args["auto_select"] = "best_promo_candidate"
            return "create_promotional_campaign", args

        # 4. Restock / Adjust stock intent
        if any(w in q for w in ["restock", "adjust stock", "replenish", "add stock", "increase stock"]):
            # Check if specific quantity mentioned
            # Prefer a number after "by/add/with/+", then a number followed by a unit word,
            # then any standalone number. Sizes inside product names ("1L", "5kg", "500g")
            # are skipped because the digits are attached to letters.
            qty_match = (
                re.search(r'(?:\bby|\badd|\bwith|\+)\s*(\d+)\b', q)
                or re.search(r'\b(\d+)\s*(?:units?|packs?|bottles?|items?|cartons?|boxes?|pcs|pieces)\b', q)
                or re.search(r'(?<![\w.])(\d+)(?![\w.%])', q)
            )
            qty = int(qty_match.group(1)) if qty_match else 25

            # Check if user specifically asks a question: "which products need restock"
            is_inquiry = (
                re.search(r'\b(which|who|what)\b', q) is not None
                and re.search(r'\b(by|with|add)\b', q) is None
            )

            target_p = resolve_target_product()

            if is_inquiry and not target_p:
                return "get_restock_recommendations", {}

            args = {
                "product_name": target_p or "",
                "quantity": qty,
                "adjustment_type": "RESTOCK",
                "notes": f"Triggered via Copilot replenishment request (Context: {target_p or 'lead'})"
            }
            # "Restock top low-stock item by 30" -> the most urgent low-stock product
            if not target_p and re.search(r"\b(top|most|lowest|urgent|critical|low|neediest)\b", q):
                args["auto_select"] = "most_urgent_restock"
            return "adjust_inventory_stock", args

        # 5. Restock recommendation inquiry
        if any(w in q for w in ["low stock", "reorder threshold", "depleted", "shortage", "out of stock", "running low"]):
            return "get_restock_recommendations", {}

        # 6. Discount recommendations for surplus stock
        if any(w in q for w in ["recommended discount", "clearance", "dead stock", "slow moving", "surplus", "discount strategy"]):
            return "get_discount_recommendations", {"max_discount_pct": 15.0}

        # The time period is passed as the merchant's own words; the tools read it with
        # the shared parse_period() helper ("last 5 days", "yesterday", "this week", ...).
        period_phrase = query
        has_sales_words = SALES_WORDS.search(q) is not None
        is_overview = re.search(r"\b(overview|snapshot|health|status)\b", q) is not None

        # 7. Compare named products: "compare milk and rice sales", "oil vs salt"
        if re.search(r"\bcompare\b|\bcomparison\b|\bvs\.?\b|\bversus\b", q):
            return "compare_products", {
                "product_names": self._match_all_products_in_text(q, products),
                "period": period_phrase,
            }

        # 7b. Two or more products named in a sales/analysis question -> compare them,
        #     even without the word "compare": "analyze atta then analyze tea",
        #     "which sold more, milk or rice", "milk and rice sales this week"
        named = self._match_all_products_in_text(q, products)
        if len(named) >= 2 and (has_sales_words or ANALYZE_WORDS.search(q) or CHART_WORDS.search(q)
                                or re.search(r"\b(more|better|higher)\b", q)):
            return "compare_products", {"product_names": named, "period": period_phrase}

        # 8. Rankings across products: "most sold items last 5 days", "best seller",
        #    "which items are not selling", "top 3 products by revenue"
        is_top = RANK_TOP.search(q) is not None
        is_bottom = RANK_BOTTOM.search(q) is not None
        if (is_top or is_bottom) and (has_sales_words or PRODUCT_WORDS.search(q)):
            # "Analyze performance of our top product" -> analyze that one product
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

        # 9. One named product + a sales/performance question: "how is milk selling this week"
        target_p = self._match_product_in_text(q, products)
        if target_p and (has_sales_words or ANALYZE_WORDS.search(q)):
            return "analyze_product_performance", {"product_name": target_p, "period": period_phrase}

        # 10. Analyze / performance wording
        if ANALYZE_WORDS.search(q) or "sales of" in q:
            target_p = resolve_target_product()
            if target_p:
                return "analyze_product_performance", {"product_name": target_p, "period": period_phrase}
            if not is_overview:
                # No product named ("how did I do yesterday", "analyze performance last 14 days")
                # -> store-wide sales summary for that period
                return "get_sales_summary", {"period": period_phrase}

        # 11. Store-wide sales totals: "how much did I sell yesterday", "sales for last 7 days"
        if not is_overview and (
            has_sales_words
            or re.search(r"\bhow\s+(?:much|many)\b", q)
            or re.search(r"\bsales?\s+summary\b", q)
        ):
            return "get_sales_summary", {"period": period_phrase}

        # 12. Store overview / business snapshot
        overview_patterns = [r'\boverview\b', r'\bsummary\b', r'\bsnapshot\b', r'\bstatus\b', r'\bhealth\b', r'\bhello\b', r'\bhi\b', r'\bhelp\b']
        if any(re.search(pat, q) for pat in overview_patterns):
            return "get_business_overview", {}

        # 13. Only a time period ("how was yesterday?", "this week?") -> sales summary.
        #     Not when the question is about something else ("what's the weather today").
        if parse_period(q).explicit and not self._has_unmatched_words(q):
            return "get_sales_summary", {"period": period_phrase}

        # 14. Could not be mapped to any store tool
        return None, {}


agent_tool_parser = AgentToolParser()
