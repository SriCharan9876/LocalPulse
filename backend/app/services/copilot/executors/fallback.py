"""
Fallback execution mixin for Copilot Agent tools:
- execute_unmapped_fallback
"""

from typing import List, Optional
from app.schemas.copilot import CopilotChatResponse


class FallbackExecutorMixin:
    """Handles unmapped user intents and guidance messages."""

    def execute_unmapped_fallback(self, query: str, products: Optional[List[dict]] = None) -> CopilotChatResponse:
        """Fallback when user intent cannot be mapped to any operational tool."""
        names = [p.get("name", "") for p in (products or []) if p.get("name")]
        a = names[0] if names else "Milk"
        b = names[1] if len(names) > 1 else "Bread"
        short = lambda n: " ".join(n.split()[:3])
        a, b = short(a), short(b)
        reply = (
            f"**I couldn't match that to a store action yet**\n\n"
            f"I'm not sure how to answer *\"{query}\"*. Try asking it like one of these:\n\n"
            f"Here are all the operational capabilities I support for your store:\n"
            f"1. **Neighborhood Map & Stores:** *\"Who are the closest stores near me?\"* or *\"Find nearby bakery within 1 km\"*\n"
            f"2. **Festivals & Events:** *\"What events are coming up on the local calendar?\"* or *\"Action plan for Diwali\"*\n"
            f"3. **Cross-Store Collaboration:** *\"Discover collaboration partners for {a}\"* or *\"Propose a joint combo with Krishna Bakery\"*\n"
            f"4. **Demand Forecasting:** *\"Show 7-day demand forecast for {a}\"* or *\"Which products have high stockout risk next week?\"*\n"
            f"5. **Inventory Restock & Loss:** *\"Restock {a} by 25 units\"* or *\"Record 4 units of {b} damaged as loss\"*\n"
            f"6. **Top / Slow Sellers:** *\"What are my top selling products this week?\"* or *\"Which items are not selling?\"*\n"
            f"7. **Sales Summary:** *\"How much did I sell yesterday?\"* or *\"Sales for the last 30 days\"*\n"
            f"8. **Compare Products:** *\"Compare {a} and {b} sales\"*\n"
            f"9. **Product Analytics:** *\"Analyze {a} sales over the last 14 days\"*\n"
            f"10. **Clearance Discounts:** *\"Recommend discounts to clear surplus inventory\"*\n"
            f"11. **Campaigns:** *\"Draft a 10% weekend offer on {b}\"* or *\"End active campaign\"*\n"
            f"12. **Add Catalog Product:** *\"Add new product Oat Milk, cost 60, sell 95, stock 40\"*\n"
            f"13. **Store Health Overview:** *\"Show me my business snapshot\"*"
        )

        return CopilotChatResponse(
            reply=reply,
            evidence=[],
            draft_action=None,
            llm_configured=True,
            provider_info="LocalPulse Agent: Unmapped Intent Fallback",
        )
