"""
Base executor mixin and spatial helpers for Copilot Agent tools.
"""

import math
import re
from typing import List, Optional
from app.schemas.copilot import CopilotChatResponse


def calculate_haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Returns distance in kilometers using the Haversine formula."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)


class BaseExecutorMixin:
    """Shared execution helper utilities."""

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
