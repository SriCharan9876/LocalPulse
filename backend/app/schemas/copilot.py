from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Any
from datetime import datetime

class DraftAction(BaseModel):
    action_type: str  # "RESTOCK_INVENTORY", "CREATE_CAMPAIGN", "CREATE_COLLABORATION_PROPOSAL"
    title: str
    description: str
    payload: dict  # Parameters required to execute the action
    requires_confirmation: bool = True
    status: str = "PENDING_CONFIRMATION"  # "PENDING_CONFIRMATION", "CONFIRMED", "CANCELLED"

class CopilotEvidenceItem(BaseModel):
    source_metric: str
    value: str
    context: str

class ChartPoint(BaseModel):
    label: str              # short label shown on the chart, e.g. "Amul Taaza Milk" or "Sat 25"
    value: float
    full_label: Optional[str] = None  # full product name / date, shown on hover

class ChartData(BaseModel):
    """Minimal chart attached to an analytics reply. Shown only when the merchant asks for it."""
    kind: str = "bars"      # "bars" = horizontal bars (products), "columns" = vertical bars (days)
    title: str
    value_label: str        # e.g. "Revenue", "Units sold"
    value_prefix: str = ""  # "₹" for money
    points: List[ChartPoint]
    auto_open: bool = False  # True when the merchant explicitly asked for a chart

class CopilotChatMessage(BaseModel):
    role: str  # "user", "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    evidence: Optional[List[CopilotEvidenceItem]] = None
    draft_action: Optional[DraftAction] = None

class CopilotChatRequest(BaseModel):
    message: Optional[str] = None
    query: Optional[str] = None

    @model_validator(mode='before')
    @classmethod
    def resolve_message_or_query(cls, data: Any):
        if isinstance(data, dict):
            text = data.get("message") or data.get("query")
            if not text or not str(text).strip():
                raise ValueError("A non-empty 'message' or 'query' must be provided.")
            data["message"] = str(text).strip()
            data["query"] = str(text).strip()
        elif isinstance(data, str):
            text = data.strip()
            if not text:
                raise ValueError("Message cannot be empty.")
            return {"message": text, "query": text}
        return data

class CopilotChatResponse(BaseModel):
    message_id: Optional[str] = None
    reply: str
    evidence: List[CopilotEvidenceItem] = Field(default_factory=list)
    draft_action: Optional[DraftAction] = None
    llm_configured: bool
    provider_info: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    chart: Optional[ChartData] = None
    llm_rate_limited: Optional[bool] = False

class ActionConfirmationRequest(BaseModel):
    action_type: str
    payload: dict

class ActionConfirmationResponse(BaseModel):
    success: bool
    message: str
    executed_action_type: str
    result_data: Optional[dict] = None

class CopilotMessageResponse(BaseModel):
    message_id: str
    role: str
    content: str
    timestamp: datetime
    evidence: Optional[List[CopilotEvidenceItem]] = None
    draft_action: Optional[DraftAction] = None
    confirmation_message: Optional[str] = None
    provider_info: Optional[str] = None
    chart: Optional[ChartData] = None

class CopilotHistoryResponse(BaseModel):
    messages: List[CopilotMessageResponse]

class VoiceTranscriptionResponse(BaseModel):
    success: bool
    transcript: str
    language_code: Optional[str] = None
    provider: str
    model: Optional[str] = None
    error: Optional[str] = None

