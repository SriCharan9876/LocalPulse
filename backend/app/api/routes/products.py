import uuid
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.session import get_database
from app.api.dependencies import get_current_merchant
from app.schemas.product import (
    ProductCreate, ProductUpdate, ProductResponse,
    InventoryAdjustmentRequest, InventoryMovementResponse
)

router = APIRouter(prefix="/products", tags=["Products & Inventory"])

@router.get("", response_model=List[ProductResponse])
async def list_products(
    merchant: dict = Depends(get_current_merchant),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """List all products owned by the authenticated merchant."""
    cursor = db.products.find({"merchant_id": merchant["merchant_id"]})
    products = await cursor.to_list(length=200)
    return [
        ProductResponse(
            product_id=p["product_id"],
            merchant_id=p["merchant_id"],
            name=p["name"],
            category=p.get("category", "General"),
            cost_price=float(p["cost_price"]),
            selling_price=float(p["selling_price"]),
            effective_selling_price=float(p.get("effective_selling_price", p["selling_price"])),
            active_campaign_id=p.get("active_campaign_id"),
            current_stock=int(p["current_stock"]),
            reorder_threshold=int(p.get("reorder_threshold", 10)),
            unit=p.get("unit", "units"),
            created_at=p.get("created_at", datetime.utcnow()),
            updated_at=p.get("updated_at", datetime.utcnow()),
        )
        for p in products
    ]

@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    req: ProductCreate,
    merchant: dict = Depends(get_current_merchant),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Create a new product under the authenticated merchant's catalog."""
    m_id = merchant["merchant_id"]
    p_id = f"prod-{m_id[:8]}-{uuid.uuid4().hex[:6]}"
    now = datetime.utcnow()

    effective_price = req.effective_selling_price or req.selling_price

    prod_doc = {
        "product_id": p_id,
        "merchant_id": m_id,
        "name": req.name,
        "category": req.category,
        "cost_price": req.cost_price,
        "selling_price": req.selling_price,
        "effective_selling_price": effective_price,
        "active_campaign_id": None,
        "current_stock": req.current_stock,
        "reorder_threshold": req.reorder_threshold,
        "unit": req.unit,
        "created_at": now,
        "updated_at": now,
        "is_synthetic": merchant.get("is_synthetic", False),
    }
    await db.products.insert_one(prod_doc)

    # Initial movement log if starting stock > 0
    if req.current_stock > 0:
        mov_doc = {
            "movement_id": f"mov-{uuid.uuid4().hex[:10]}",
            "merchant_id": m_id,
            "product_id": p_id,
            "product_name": req.name,
            "adjustment_type": "AUDIT_CORRECTION",
            "quantity_change": req.current_stock,
            "stock_before": 0,
            "stock_after": req.current_stock,
            "notes": "Initial catalog intake stock",
            "created_at": now,
            "is_synthetic": prod_doc["is_synthetic"],
        }
        await db.inventory_movements.insert_one(mov_doc)

    return ProductResponse(**prod_doc)

@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    req: ProductUpdate,
    merchant: dict = Depends(get_current_merchant),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Update product metadata or pricing."""
    m_id = merchant["merchant_id"]
    product = await db.products.find_one({"merchant_id": m_id, "product_id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    update_fields = {}
    if req.name is not None:
        update_fields["name"] = req.name
    if req.category is not None:
        update_fields["category"] = req.category
    if req.cost_price is not None:
        update_fields["cost_price"] = req.cost_price
    if req.selling_price is not None:
        update_fields["selling_price"] = req.selling_price
    if req.reorder_threshold is not None:
        update_fields["reorder_threshold"] = req.reorder_threshold
    if req.unit is not None:
        update_fields["unit"] = req.unit
    
    update_fields["updated_at"] = datetime.utcnow()

    await db.products.update_one(
        {"merchant_id": m_id, "product_id": product_id},
        {"$set": update_fields}
    )
    updated = await db.products.find_one({"merchant_id": m_id, "product_id": product_id})
    return ProductResponse(**updated)

@router.post("/{product_id}/adjust-inventory", response_model=InventoryMovementResponse)
async def adjust_inventory(
    product_id: str,
    req: InventoryAdjustmentRequest,
    merchant: dict = Depends(get_current_merchant),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Audited inventory adjustment.
    Updates stock balance and creates immutable movement record.
    """
    m_id = merchant["merchant_id"]
    product = await db.products.find_one({"merchant_id": m_id, "product_id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    stock_before = int(product.get("current_stock", 0))
    qty = req.quantity

    if req.adjustment_type == "RESTOCK":
        stock_after = stock_before + qty
        qty_change = qty
    elif req.adjustment_type in ("DAMAGE_LOSS", "AUDIT_CORRECTION"):
        # For damage or correction, deduct or ensure non-negative
        stock_after = max(0, stock_before - qty)
        qty_change = -(stock_before - stock_after)
    else:
        raise HTTPException(status_code=400, detail="Invalid adjustment type")

    now = datetime.utcnow()
    await db.products.update_one(
        {"merchant_id": m_id, "product_id": product_id},
        {"$set": {"current_stock": stock_after, "updated_at": now}}
    )

    mov_doc = {
        "movement_id": f"mov-{uuid.uuid4().hex[:10]}",
        "merchant_id": m_id,
        "product_id": product_id,
        "product_name": product["name"],
        "adjustment_type": req.adjustment_type,
        "quantity_change": qty_change,
        "stock_before": stock_before,
        "stock_after": stock_after,
        "notes": req.notes or f"Manual {req.adjustment_type} adjustment",
        "created_at": now,
    }
    await db.inventory_movements.insert_one(mov_doc)

    return InventoryMovementResponse(**mov_doc)

@router.get("/{product_id}/movements", response_model=List[InventoryMovementResponse])
async def list_inventory_movements(
    product_id: str,
    merchant: dict = Depends(get_current_merchant),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get audit trail of inventory movements for this product."""
    m_id = merchant["merchant_id"]
    cursor = db.inventory_movements.find(
        {"merchant_id": m_id, "product_id": product_id}
    ).sort("created_at", -1)
    movements = await cursor.to_list(length=50)
    return [InventoryMovementResponse(**m) for m in movements]
