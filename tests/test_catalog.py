from __future__ import annotations

from decimal import Decimal

import pytest

from shopkit.catalog import Catalog, Product
from shopkit.errors import InvalidAmountError, UnknownProductError
from tests.conftest import MUG, TEA


def test_lookup_by_sku() -> None:
    catalog = Catalog([TEA, MUG])
    assert catalog.get("MUG-STONE") is MUG
    assert "TEA-GREEN" in catalog
    assert len(catalog) == 2
    assert list(catalog) == [TEA, MUG]


def test_unknown_sku() -> None:
    with pytest.raises(UnknownProductError, match="NOPE"):
        Catalog([TEA]).get("NOPE")


def test_duplicate_sku_is_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate SKU"):
        Catalog([TEA, TEA])


@pytest.mark.parametrize("sku", ["", "tea", "A", "TEA GREEN", "X" * 33])
def test_invalid_sku(sku: str) -> None:
    with pytest.raises(ValueError, match="invalid SKU"):
        Product(sku, "Tea", Decimal("1.00"))


def test_negative_price_and_empty_name_are_rejected() -> None:
    with pytest.raises(InvalidAmountError):
        Product("TEA-1", "Tea", Decimal("-1.00"))
    with pytest.raises(ValueError, match="name"):
        Product("TEA-1", "  ", Decimal("1.00"))
