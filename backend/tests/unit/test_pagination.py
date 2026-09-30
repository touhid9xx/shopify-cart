from __future__ import annotations

import pytest

from shopify_cart.core.pagination import MAX_PAGE_SIZE, PageParams, build_page


def test_page_params_offset() -> None:
    assert PageParams(page=1, size=20).offset == 0
    assert PageParams(page=2, size=20).offset == 20
    assert PageParams(page=5, size=10).offset == 40


def test_page_params_rejects_zero_page() -> None:
    with pytest.raises(ValueError):
        PageParams(page=0)


def test_page_params_rejects_oversized_page() -> None:
    with pytest.raises(ValueError):
        PageParams(size=MAX_PAGE_SIZE + 1)


def test_build_page_computes_pages() -> None:
    p = build_page([1, 2, 3], total=10, params=PageParams(page=1, size=3))
    assert p.total == 10
    assert p.pages == 4  # ceil(10/3)
    assert p.items == [1, 2, 3]


def test_build_page_exact_multiple() -> None:
    p = build_page([], total=20, params=PageParams(page=1, size=20))
    assert p.pages == 1
