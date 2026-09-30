from __future__ import annotations

from shopify_cart.db.base import NAMING_CONVENTION


def test_naming_convention_keys() -> None:
    for key in ("ix", "uq", "ck", "fk", "pk"):
        assert key in NAMING_CONVENTION
        assert "%(" in NAMING_CONVENTION[key]
