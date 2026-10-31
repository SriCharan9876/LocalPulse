from datetime import datetime, date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.session import get_database
from app.api.dependencies import get_current_merchant
from app.services.forecasting import forecasting_service
from app.schemas.forecast import ProductForecastResponse, BatchForecastSummary
from app.schemas.sales import ProductSalesHistoryResponse, DailySaleRecord

router = APIRouter(prefix="/demand", tags=["Demand Forecasting & History"])

@router.get("/forecasts", response_model=BatchForecastSummary)
async def get_forecasts(
    product_id: Optional[str] = Query(None, description="Optional single product ID filter"),
    days: int = Query(7, ge=1, le=14),
    merchant: dict = Depends(get_current_merchant),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Generate 7-day demand forecasts for the authenticated merchant's products.
    Uses transparent weekday-aware historical baseline model.
    """
    m_id = merchant["merchant_id"]
    prod_filter = {"merchant_id": m_id}
    if product_id:
        prod_filter["product_id"] = product_id

    products = await db.products.find(prod_filter).to_list(length=100)
    if not products:
        return BatchForecastSummary(
            forecast_generated_at=datetime.utcnow().isoformat(),
            forecast_horizon_days=days,
            products_analyzed=0,
            total_forecasted_units=0,
            total_projected_revenue=0.0,
            high_stockout_risk_count=0,
            forecasts=[]
        )

    forecast_results: List[ProductForecastResponse] = []
    total_units = 0
    total_revenue = 0.0
    stockout_risks = 0

    for p in products:
        sales = await db.sales.find({
            "merchant_id": m_id,
            "product_id": p["product_id"]
        }).sort("date", 1).to_list(length=120)

        fc = forecasting_service.forecast_product(p, sales, horizon_days=days)
        forecast_results.append(fc)
        total_units += fc.total_forecasted_units
        total_revenue += fc.total_projected_revenue
        if fc.stockout_risk:
            stockout_risks += 1

    return BatchForecastSummary(
        forecast_generated_at=datetime.utcnow().isoformat(),
        forecast_horizon_days=days,
        products_analyzed=len(products),
        total_forecasted_units=total_units,
        total_projected_revenue=round(total_revenue, 2),
        high_stockout_risk_count=stockout_risks,
        forecasts=forecast_results
    )

@router.get("/sales-history/{product_id}", response_model=ProductSalesHistoryResponse)
async def get_product_sales_history(
    product_id: str,
    days: int = Query(30, ge=7, le=90),
    merchant: dict = Depends(get_current_merchant),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Retrieve daily historical product-level sales records."""
    m_id = merchant["merchant_id"]
    product = await db.products.find_one({"merchant_id": m_id, "product_id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    start_date = (date.today() - timedelta(days=days)).strftime("%Y-%m-%d")
    cursor = db.sales.find({
        "merchant_id": m_id,
        "product_id": product_id,
        "date": {"$gte": start_date}
    }).sort("date", 1)
    
    sales = await cursor.to_list(length=100)
    history_records = [
        DailySaleRecord(
            date=s["date"],
            units_sold=int(s.get("units_sold", 0)),
            revenue=float(s.get("revenue", 0.0)),
            cogs=float(s.get("cogs", 0.0)),
            gross_profit=float(s.get("gross_profit", 0.0)),
        )
        for s in sales
    ]

    total_units = sum(r.units_sold for r in history_records)
    total_rev = round(sum(r.revenue for r in history_records), 2)
    avg_units = round(total_units / len(history_records), 1) if history_records else 0.0

    return ProductSalesHistoryResponse(
        product_id=product_id,
        product_name=product["name"],
        category=product.get("category", "General"),
        current_stock=int(product.get("current_stock", 0)),
        history=history_records,
        total_units_sold=total_units,
        total_revenue=total_rev,
        avg_daily_units=avg_units,
    )
