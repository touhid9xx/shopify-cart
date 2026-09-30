"""Money helpers — all monetary math goes through here.

Never use float for money. Decimal everywhere.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

TWO_PLACES = Decimal("0.01")


def quantize_money(value: Decimal) -> Decimal:
    """Round a Decimal to 2 places using banker-safe HALF_UP."""
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def multiply_money(unit_price: Decimal, quantity: int) -> Decimal:
    """Line subtotal = unit_price * quantity, quantized to 2 places."""
    if quantity < 0:
        raise ValueError("quantity must be >= 0")
    return quantize_money(unit_price * Decimal(quantity))


def sum_money(values: list[Decimal]) -> Decimal:
    """Sum a list of Decimal money values, quantized."""
    total = Decimal("0.00")
    for v in values:
        total += v
    return quantize_money(total)
