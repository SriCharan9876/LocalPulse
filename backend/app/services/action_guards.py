"""
Shared business-rule guards for copilot draft actions.

Used twice for every write action:
  1. When the copilot drafts an action (so the merchant never sees an invalid draft).
  2. When /copilot/confirm-action executes it (the payload comes back from the client,
     so it must be re-validated on the server before any DB write).

Each check returns None when the value is valid, or a human-readable error message.
Limits mirror the regular REST routes (CampaignCreate: discount 1-50%,
InventoryAdjustmentRequest: quantity > 0, ProductCreate: prices > 0).
"""

from typing import Optional, Any

MIN_DISCOUNT_PCT = 1.0
MAX_DISCOUNT_PCT = 50.0
MAX_ADJUSTMENT_QTY = 10_000

# Canonical adjustment types (same as InventoryAdjustmentRequest in schemas/product.py).
# Aliases cover older tool schemas / LLM outputs.
ADJUSTMENT_TYPE_ALIASES = {
    "RESTOCK": "RESTOCK",
    "DAMAGE_LOSS": "DAMAGE_LOSS",
    "DAMAGE_WRITE_OFF": "DAMAGE_LOSS",
    "DAMAGE": "DAMAGE_LOSS",
    "AUDIT_CORRECTION": "AUDIT_CORRECTION",
}


def to_float(value: Any) -> Optional[float]:
    """Safely convert a client/LLM-supplied value to float (None if not numeric)."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def to_int(value: Any) -> Optional[int]:
    """Safely convert a client/LLM-supplied value to int (None if not numeric)."""
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def normalize_adjustment_type(raw: Any) -> Optional[str]:
    """Map an adjustment type to its canonical name, or None if unknown."""
    return ADJUSTMENT_TYPE_ALIASES.get(str(raw or "RESTOCK").strip().upper())


def check_quantity(qty: Optional[int]) -> Optional[str]:
    if qty is None:
        return "Quantity must be a whole number."
    if qty <= 0:
        return "Quantity must be greater than 0."
    if qty > MAX_ADJUSTMENT_QTY:
        return f"Quantity {qty} is unusually large (limit {MAX_ADJUSTMENT_QTY:,}). Please check the number."
    return None


def check_discount(discount_pct: Optional[float]) -> Optional[str]:
    if discount_pct is None:
        return "Discount must be a number."
    if not (MIN_DISCOUNT_PCT <= discount_pct <= MAX_DISCOUNT_PCT):
        return (
            f"Discount must be between {MIN_DISCOUNT_PCT:g}% and {MAX_DISCOUNT_PCT:g}% "
            f"(got {discount_pct:g}%)."
        )
    return None


def max_discount_above_cost(product: dict) -> float:
    """Largest whole-number discount % that keeps the price at or above cost price."""
    sp = to_float(product.get("selling_price")) or 0.0
    cp = to_float(product.get("cost_price")) or 0.0
    if sp <= 0:
        return 0.0
    return max(0.0, float(int((sp - cp) / sp * 100.0)))


def check_discount_vs_cost(product: dict, discount_pct: float) -> Optional[str]:
    """Reject a discount that would push the selling price below cost price."""
    sp = to_float(product.get("selling_price")) or 0.0
    cp = to_float(product.get("cost_price")) or 0.0
    discounted = round(sp * (1.0 - discount_pct / 100.0), 2)
    if discounted < cp:
        return (
            f"{discount_pct:g}% off '{product.get('name', 'product')}' gives ₹{discounted:,.2f}, "
            f"below its cost price of ₹{cp:,.2f}. Maximum discount without a loss is "
            f"{max_discount_above_cost(product):g}%."
        )
    return None


def check_new_product(name: str, cost_price: Optional[float], selling_price: Optional[float]) -> Optional[str]:
    if not name or len(name.strip()) < 2:
        return "Product name must be at least 2 characters."
    if cost_price is None or cost_price <= 0:
        return "Cost price must be a number greater than 0."
    if selling_price is None or selling_price <= 0:
        return "Selling price must be a number greater than 0."
    if selling_price < cost_price:
        return (
            f"Selling price ₹{selling_price:,.2f} is below cost price ₹{cost_price:,.2f}; "
            "every sale would be a loss."
        )
    return None
