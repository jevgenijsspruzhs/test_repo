from __future__ import annotations

from decimal import Decimal

import pytest

from shopkit.cart import Cart
from shopkit.catalog import Product
from shopkit.vat import VatCategory

TEA = Product("TEA-GREEN", "Green tea, 100 g", Decimal("4.90"), VatCategory.REDUCED)
MUG = Product("MUG-STONE", "Stoneware mug", Decimal("18.00"), VatCategory.STANDARD)
BOOK = Product("BOOK-BREW", "The Art of Brewing", Decimal("25.00"), VatCategory.REDUCED)
LAMP = Product("LAMP-DESK", "Desk lamp", Decimal("60.00"), VatCategory.STANDARD)


@pytest.fixture
def cart() -> Cart:
    """3 x tea (14.70, reduced), 2 x mug (36.00, standard), 1 x book (25.00, reduced)."""
    result = Cart()
    result.add(TEA, 3)
    result.add(MUG, 2)
    result.add(BOOK, 1)
    return result
