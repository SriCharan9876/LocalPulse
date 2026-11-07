import asyncio
import uuid
from datetime import datetime, date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.session import get_database
from app.api.dependencies import get_current_merchant
from app.services.copilot import copilot_service
from app.services.sarvam_voice import sarvam_voice_service
from app.services.forecasting import load_relevant_events
from app.schemas.copilot import (
    CopilotChatRequest, CopilotChatResponse,
    ActionConfirmationRequest, ActionConfirmationResponse,
    CopilotMessageResponse, CopilotHistoryResponse,
    VoiceTranscriptionResponse, ChartData,
)

router = APIRouter(prefix="/copilot", tags=["AI Business Copilot"])


def _history_chart(raw):
    """Saved chart data -> ChartData (ignored if missing or malformed)."""
    if not raw:
        return None
    try:
        return ChartData(**raw)
    except Exception:
        return None

@router.get("/history", response_model=CopilotHistoryResponse)
async def get_copilot_history(
    limit: int = 50,
    merchant: dict = Depends(get_current_merchant),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Retrieve persisted conversation history for the authenticated merchant.
    Maintains isolated multi-turn memory per merchant account.
    """
    m_id = merchant["merchant_id"]
    cursor = db.copilot_messages.find({"merchant_id": m_id}).sort("created_at", 1).limit(limit)
    raw_docs = await cursor.to_list(length=limit)

    formatted = []
    for doc in raw_docs:
        formatted.append(
            CopilotMessageResponse(
                message_id=doc.get("message_id", f"cmsg-{uuid.uuid4().hex[:8]}"),
                role=doc.get("role", "assistant"),
                content=doc.get("content", ""),
                timestamp=doc.get("created_at", datetime.utcnow()),
                evidence=doc.get("evidence", []),
                draft_action=doc.get("draft_action"),
                confirmation_message=doc.get("confirmation_message"),
                provider_info=doc.get("provider_info"),
                chart=_history_chart(doc.get("chart")),
            )
        )

    return CopilotHistoryResponse(messages=formatted)

@router.delete("/history")
async def clear_copilot_history(
    merchant: dict = Depends(get_current_merchant),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Clear persisted conversation history for the authenticated merchant context.
    """
    m_id = merchant["merchant_id"]
    result = await db.copilot_messages.delete_many({"merchant_id": m_id})
    return {
        "success": True,
        "message": f"Cleared {result.deleted_count} message(s) from copilot memory.",
        "merchant_id": m_id
    }

@router.post("/chat", response_model=CopilotChatResponse)
async def chat_with_copilot(
    req: CopilotChatRequest,
    merchant: dict = Depends(get_current_merchant),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Conversational Copilot grounded strictly in the authenticated merchant's live data.
    Utilizes recent conversation memory to resolve context and pronouns, and persists
    messages to MongoDB per merchant.
    """
    m_id = merchant["merchant_id"]
    now = datetime.utcnow()

    # 1. Fetch recent conversation memory for this merchant (last 8 turns)
    cursor = db.copilot_messages.find({"merchant_id": m_id}).sort("created_at", -1).limit(8)
    recent_raw = await cursor.to_list(length=8)
    history = list(reversed(recent_raw))

    # 2. Persist the user's incoming message
    user_msg_id = f"cmsg-u-{uuid.uuid4().hex[:10]}"
    user_doc = {
        "message_id": user_msg_id,
        "merchant_id": m_id,
        "role": "user",
        "content": req.message,
        "evidence": [],
        "draft_action": None,
        "confirmation_message": None,
        "provider_info": None,
        "created_at": now,
    }
    await db.copilot_messages.insert_one(user_doc)

    # 3. Retrieve store live state concurrently via asyncio.gather for minimum latency
    sales_since = (date.today() - timedelta(days=200)).isoformat()
    products_task = db.products.find({"merchant_id": m_id}).to_list(length=100)
    sales_task = db.sales.find(
        {"merchant_id": m_id, "date": {"$gte": sales_since}}
    ).sort("date", -1).to_list(length=None)
    campaigns_task = db.campaigns.find({"merchant_id": m_id}).to_list(length=20)
    collaborations_task = db.collaborations.find({
        "$or": [{"initiator_merchant_id": m_id}, {"partner_merchant_id": m_id}]
    }).to_list(length=20)
    events_task = load_relevant_events(db, merchant)

    products, sales, campaigns, collaborations, events = await asyncio.gather(
        products_task, sales_task, campaigns_task, collaborations_task, events_task
    )

    # 4. Process chat with memory context
    response = await copilot_service.process_chat(
        query=req.message,
        merchant=merchant,
        products=products,
        recent_sales=sales,
        campaigns=campaigns,
        collaborations=collaborations,
        history=history,
        events=events,
        db=db,
    )

    # 5. Persist the assistant's response in database
    asst_msg_id = f"cmsg-a-{uuid.uuid4().hex[:10]}"
    response.message_id = asst_msg_id

    asst_doc = {
        "message_id": asst_msg_id,
        "merchant_id": m_id,
        "role": "assistant",
        "content": response.reply,
        "evidence": [e.dict() for e in response.evidence],
        "draft_action": response.draft_action.dict() if response.draft_action else None,
        "confirmation_message": None,
        "provider_info": response.provider_info,
        # Saved closed: after a reload the chart is offered again, not forced open
        "chart": ({**response.chart.model_dump(), "auto_open": False} if response.chart else None),
        "created_at": datetime.utcnow(),
    }
    await db.copilot_messages.insert_one(asst_doc)

    return response

@router.post("/confirm-action", response_model=ActionConfirmationResponse)
async def confirm_copilot_action(
    req: ActionConfirmationRequest,
    merchant: dict = Depends(get_current_merchant),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Explicit confirmation endpoint for write actions drafted by the Copilot.
    Validates business rules, executes DB mutation, and updates persisted message audit status.
    """
    m_id = merchant["merchant_id"]
    execution_result = await copilot_service.execute_confirmed_action(
        action_type=req.action_type,
        payload=req.payload,
        merchant=merchant,
        db=db,
    )

    if execution_result.success:
        # Mark the most recent pending draft action in memory as confirmed.
        # find_one(sort=...) + update by _id instead of update_one(sort=...): the sort
        # option on update_one needs MongoDB 8.0+ and is not supported by the in-memory
        # mongomock fallback, where it raised a 500 AFTER the DB write had already happened.
        pending = await db.copilot_messages.find_one(
            {
                "merchant_id": m_id,
                "draft_action.action_type": req.action_type,
                "draft_action.status": "PENDING_CONFIRMATION"
            },
            sort=[("created_at", -1)],
        )
        if pending:
            await db.copilot_messages.update_one(
                {"_id": pending["_id"]},
                {
                    "$set": {
                        "draft_action.status": "CONFIRMED",
                        "confirmation_message": execution_result.message,
                        "updated_at": datetime.utcnow()
                    }
                },
            )

    return execution_result


@router.post("/voice-to-text", response_model=VoiceTranscriptionResponse)
async def convert_voice_to_text(
    audio: UploadFile = File(...),
    language_code: Optional[str] = Form(None),
    mode: str = Form("transcribe"),
    merchant: dict = Depends(get_current_merchant)
):
    """
    Multilingual Voice-to-Text conversion powered by Sarvam AI Saaras model.
    Accepts recorded audio in any Indian language or English (Hindi, Tamil, Telugu,
    Kannada, Bengali, Marathi, etc.) and returns accurate transcript text.
    """
    if not sarvam_voice_service.is_configured:
        raise HTTPException(
            status_code=503,
            detail=(
                "Sarvam AI is not configured. Please add SARVAM_API_KEY in backend/.env "
                "to enable multilingual voice input."
            )
        )

    try:
        audio_bytes = await audio.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio file uploaded.")

        filename = audio.filename or "recording.webm"
        content_type = audio.content_type or "audio/webm"

        result = await sarvam_voice_service.transcribe_audio(
            audio_bytes=audio_bytes,
            filename=filename,
            content_type=content_type,
            language_code=language_code,
            mode=mode
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=502,
                detail=result.get("error", "Failed to transcribe audio via Sarvam AI.")
            )

        return VoiceTranscriptionResponse(
            success=True,
            transcript=result.get("transcript", ""),
            language_code=result.get("language_code"),
            provider=result.get("provider", "Sarvam AI"),
            model=result.get("model", "saaras:v4"),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice processing error: {str(e)}")

