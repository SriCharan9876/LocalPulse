"""
Product and inventory movement domain service.
Handles product catalog CRUD and audited stock adjustments.
"""

import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    InventoryAdjustmentRequest,
    InventoryMovementResponse,
)


class ProductService:
    async def list_products(
        self,
        db: AsyncIOMotorDatabase,
        merchant_id: str,
    ) -> List[ProductResponse]:
        """List all catalog items owned by the merchant."""
        cursor = db.products.find({"merchant_id": merchant_id})
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

    async def create_product(
        self,
        db: AsyncIOMotorDatabase,
        merchant: dict,
        req: ProductCreate,
    ) -> ProductResponse:
        """Create a new catalog item and write initial intake inventory audit."""
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

    async def update_product(
        self,
        db: AsyncIOMotorDatabase,
        merchant_id: str,
        product_id: str,
        req: ProductUpdate,
    ) -> ProductResponse:
        """Update product pricing, name, or metadata."""
        product = await db.products.find_one({"merchant_id": merchant_id, "product_id": product_id})
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

        update_fields = {}
        if req.name is not None:
            update_fields["name"] = req.name
        if req.category is not None:
            update_fields["category"] = req.category
        if req.cost_price is not None:
            update_fields["cost_price"] = req.cost_price
        if req.selling_price is not None:
            update_fields["selling_price"] = req.selling_price
        if req.effective_selling_price is not None:
            update_fields["effective_selling_price"] = req.effective_selling_price
        if req.reorder_threshold is not None:
            update_fields["reorder_threshold"] = req.reorder_threshold
        if req.unit is not None:
            update_fields["unit"] = req.unit

        update_fields["updated_at"] = datetime.utcnow()

        await db.products.update_one(
            {"merchant_id": merchant_id, "product_id": product_id},
            {"$set": update_fields}
        )
        updated = await db.products.find_one({"merchant_id": merchant_id, "product_id": product_id})
        return ProductResponse(**updated)

    async def adjust_inventory(
        self,
        db: AsyncIOMotorDatabase,
        merchant_id: str,
        product_id: str,
        req: InventoryAdjustmentRequest,
    ) -> InventoryMovementResponse:
        """Perform audited inventory adjustment and record movement."""
        product = await db.products.find_one({"merchant_id": merchant_id, "product_id": product_id})
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

        stock_before = int(product.get("current_stock", 0))
        qty = req.quantity

        if req.adjustment_type == "RESTOCK":
            stock_after = stock_before + qty
            qty_change = qty
        elif req.adjustment_type in ("DAMAGE_LOSS", "AUDIT_CORRECTION"):
            stock_after = max(0, stock_before - qty)
            qty_change = -(stock_before - stock_after)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid adjustment type")

        now = datetime.utcnow()
        await db.products.update_one(
            {"merchant_id": merchant_id, "product_id": product_id},
            {"$set": {"current_stock": stock_after, "updated_at": now}}
        )

        mov_doc = {
            "movement_id": f"mov-{uuid.uuid4().hex[:10]}",
            "merchant_id": merchant_id,
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

    async def list_movements(
        self,
        db: AsyncIOMotorDatabase,
        merchant_id: str,
        product_id: str,
    ) -> List[InventoryMovementResponse]:
        """Fetch audit log history of movements for a product."""
        cursor = db.inventory_movements.find(
            {"merchant_id": merchant_id, "product_id": product_id}
        ).sort("created_at", -1)
        movements = await cursor.to_list(length=50)
        return [InventoryMovementResponse(**m) for m in movements]


product_service = ProductService()

