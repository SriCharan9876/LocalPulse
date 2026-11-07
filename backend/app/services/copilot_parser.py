"""
Backwards-compatibility shim for copilot_parser.
Modularized code is now organized in `app.services.copilot.parser`.
"""

from app.services.copilot.parser import (
    AgentToolParser,
    agent_tool_parser,
    SALES_WORDS,
    RANK_TOP,
    RANK_BOTTOM,
    PRODUCT_WORDS,
    CHART_WORDS,
    ANALYZE_WORDS,
)

__all__ = [
    "AgentToolParser",
    "agent_tool_parser",
    "SALES_WORDS",
    "RANK_TOP",
    "RANK_BOTTOM",
    "PRODUCT_WORDS",
    "CHART_WORDS",
    "ANALYZE_WORDS",
]
