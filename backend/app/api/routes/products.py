from typing import List
from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.session import get_database
from app.api.dependencies import get_current_merchant
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    InventoryAdjustmentRequest,
    InventoryMovementResponse,
)
from app.services.product import product_service

router = APIRouter(prefix="/products", tags=["Products & Inventory"])


@router.get("", response_model=List[ProductResponse])
async def list_products(
    merchant: dict = Depends(get_current_merchant),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """List all products owned by the authenticated merchant."""
    return await product_service.list_products(db, merchant["merchant_id"])


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    req: ProductCreate,
    merchant: dict = Depends(get_current_merchant),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Create a new product under the authenticated merchant's catalog."""
    return await product_service.create_product(db, merchant, req)


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    req: ProductUpdate,
    merchant: dict = Depends(get_current_merchant),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Update product metadata or pricing."""
    return await product_service.update_product(db, merchant["merchant_id"], product_id, req)


@router.post("/{product_id}/adjust-inventory", response_model=InventoryMovementResponse)
async def adjust_inventory(
    product_id: str,
    req: InventoryAdjustmentRequest,
    merchant: dict = Depends(get_current_merchant),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Audited inventory adjustment.
    Updates stock balance and creates immutable movement record.
    """
    return await product_service.adjust_inventory(db, merchant["merchant_id"], product_id, req)


@router.get("/{product_id}/movements", response_model=List[InventoryMovementResponse])
async def list_inventory_movements(
    product_id: str,
    merchant: dict = Depends(get_current_merchant),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Get audit trail of inventory movements for this product."""
    return await product_service.list_movements(db, merchant["merchant_id"], product_id)
