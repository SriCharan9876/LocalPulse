from app.schemas.auth import (
    LoginRequest, SignupRequest, MerchantProfile, MerchantProfileUpdate, Token, SwitchDemoMerchantRequest
)
from app.schemas.product import (
    ProductCreate, ProductUpdate, ProductResponse,
    InventoryAdjustmentRequest, InventoryMovementResponse
)
from app.schemas.sales import (
    DailySaleRecord, ProductSalesHistoryResponse, OverallSalesHistoryResponse
)
from app.schemas.forecast import (
    DailyForecastPoint, ProductForecastResponse, BatchForecastSummary
)
from app.schemas.dashboard import (
    DashboardSummaryResponse, StockWarningItem, GrowthRecommendation
)
from app.schemas.collaboration import (
    DiscoverablePartner, MarginValidationRequest, MarginValidationResponse,
    CollaborationProposalCreate, CollaborationProposalResponse
)
from app.schemas.campaign import (
    CampaignCreate, SimulateRedemptionRequest, CampaignPerformanceResponse
)
from app.schemas.copilot import (
    CopilotChatRequest, CopilotChatResponse, CopilotChatMessage,
    DraftAction, CopilotEvidenceItem, ActionConfirmationRequest, ActionConfirmationResponse
)
