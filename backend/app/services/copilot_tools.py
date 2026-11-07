"""
Backwards-compatibility shim for copilot_tools.
Modularized code is now organized in `app.services.copilot.tools`.
"""

from app.services.copilot.tools import COPILOT_TOOLS

__all__ = ["COPILOT_TOOLS"]
