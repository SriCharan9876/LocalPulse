"""
Copilot Tool Executors Package.
Composes domain mixins into the unified CopilotToolExecutor.
"""

from app.services.copilot.executors.base import BaseExecutorMixin, calculate_haversine
from app.services.copilot.executors.analytics import AnalyticsExecutorMixin
from app.services.copilot.executors.inventory import InventoryExecutorMixin
from app.services.copilot.executors.campaigns import CampaignsExecutorMixin
from app.services.copilot.executors.neighborhood import NeighborhoodExecutorMixin
from app.services.copilot.executors.forecasting import ForecastingExecutorMixin
from app.services.copilot.executors.fallback import FallbackExecutorMixin


class CopilotToolExecutor(
    BaseExecutorMixin,
    AnalyticsExecutorMixin,
    InventoryExecutorMixin,
    CampaignsExecutorMixin,
    NeighborhoodExecutorMixin,
    ForecastingExecutorMixin,
    FallbackExecutorMixin,
):
    """Executes read-only operations immediately and structures mutation drafts."""
    pass


copilot_tool_executor = CopilotToolExecutor()

__all__ = [
    "CopilotToolExecutor",
    "copilot_tool_executor",
    "calculate_haversine",
]
