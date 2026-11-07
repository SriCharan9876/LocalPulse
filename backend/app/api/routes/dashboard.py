from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.session import get_database
from app.api.dependencies import get_current_merchant
from app.schemas.dashboard import DashboardSummaryResponse
from app.services.dashboard import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["Merchant Dashboard"])

@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    merchant: dict = Depends(get_current_merchant),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Consolidated merchant dashboard summary:
    - 30d indicators (revenue, orders, growth score)
    - 30d historical sales trend
    - 7-day demand forecast aggregation
    - Critical stock warnings
    - Prioritized growth recommendations

    Delegates aggregation and analytics calculation to DashboardService.
    """
    return await dashboard_service.build_dashboard_summary(db, merchant)
