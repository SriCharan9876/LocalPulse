"""
Backwards-compatibility shim for action_guards.
Modularized code is now organized in `app.services.copilot.guards`.
"""

from app.services.copilot.guards import (
    MIN_DISCOUNT_PCT,
    MAX_DISCOUNT_PCT,
    MAX_ADJUSTMENT_QTY,
    ADJUSTMENT_TYPE_ALIASES,
    to_float,
    to_int,
    normalize_adjustment_type,
    check_quantity,
    check_discount,
    max_discount_above_cost,
    check_discount_vs_cost,
    check_new_product,
)

__all__ = [
    "MIN_DISCOUNT_PCT",
    "MAX_DISCOUNT_PCT",
    "MAX_ADJUSTMENT_QTY",
    "ADJUSTMENT_TYPE_ALIASES",
    "to_float",
    "to_int",
    "normalize_adjustment_type",
    "check_quantity",
    "check_discount",
    "max_discount_above_cost",
    "check_discount_vs_cost",
    "check_new_product",
]
