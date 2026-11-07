"""
LocalPulse AI Copilot Package.
Modular architecture decomposing the AI Business Copilot into:
- service: Core conversational orchestration & confirmed mutation execution
- parser: Intent parsing (LLM function calling + deterministic heuristics)
- tools: Tool registry & JSON schema definitions
- guards: Business-rule safety validations
- executors: Domain-specific execution handlers (analytics, inventory, campaigns, neighborhood, forecasting, fallback)
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.copilot.service import CopilotService, copilot_service
    from app.services.copilot.parser import AgentToolParser, agent_tool_parser
    from app.services.copilot.tools import COPILOT_TOOLS
    from app.services.copilot.executors import CopilotToolExecutor, copilot_tool_executor


def __getattr__(name: str):
    if name in ("CopilotService", "copilot_service"):
        from app.services.copilot.service import CopilotService, copilot_service
        return copilot_service if name == "copilot_service" else CopilotService
    if name in ("AgentToolParser", "agent_tool_parser"):
        from app.services.copilot.parser import AgentToolParser, agent_tool_parser
        return agent_tool_parser if name == "agent_tool_parser" else AgentToolParser
    if name in ("CopilotToolExecutor", "copilot_tool_executor"):
        from app.services.copilot.executors import CopilotToolExecutor, copilot_tool_executor
        return copilot_tool_executor if name == "copilot_tool_executor" else CopilotToolExecutor
    if name == "COPILOT_TOOLS":
        from app.services.copilot.tools import COPILOT_TOOLS
        return COPILOT_TOOLS
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "CopilotService",
    "copilot_service",
    "AgentToolParser",
    "agent_tool_parser",
    "COPILOT_TOOLS",
    "CopilotToolExecutor",
    "copilot_tool_executor",
]
