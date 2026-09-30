from __future__ import annotations

from decimal import Decimal

import pytest

from shopify_cart.core.money import multiply_money, quantize_money, sum_money


def test_quantize_money_rounds_half_up() -> None:
    assert quantize_money(Decimal("19.995")) == Decimal("20.00")
    assert quantize_money(Decimal("19.994")) == Decimal("19.99")


def test_multiply_money() -> None:
    assert multiply_money(Decimal("19.99"), 3) == Decimal("59.97")


def test_multiply_money_rejects_negative() -> None:
    with pytest.raises(ValueError):
        multiply_money(Decimal("19.99"), -1)


def test_sum_money() -> None:
    assert sum_money([Decimal("10.00"), Decimal("5.50")]) == Decimal("15.50")


def test_sum_money_empty() -> None:
    assert sum_money([]) == Decimal("0.00")


def test_no_float_leak() -> None:
    """0.1 + 0.2 problem — Decimal should not exhibit it."""
    result = sum_money([Decimal("0.10"), Decimal("0.20")])
    assert result == Decimal("0.30")
