"""
Backwards-compatibility shim for copilot_executor.
Modularized code is now organized in `app.services.copilot.executors`.
"""

from app.services.copilot.executors import (
    CopilotToolExecutor,
    copilot_tool_executor,
    calculate_haversine,
)

__all__ = [
    "CopilotToolExecutor",
    "copilot_tool_executor",
    "calculate_haversine",
]
