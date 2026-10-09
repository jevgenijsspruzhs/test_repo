from __future__ import annotations

from decimal import Decimal

import pytest

from shopkit.cart import MAX_QUANTITY, Cart
from shopkit.catalog import Product
from shopkit.errors import UnknownProductError
from tests.conftest import BOOK, MUG, TEA


def test_lines_keep_insertion_order(cart: Cart) -> None:
    assert [line.product.sku for line in cart.lines] == ["TEA-GREEN", "MUG-STONE", "BOOK-BREW"]


def test_subtotal_and_item_count(cart: Cart) -> None:
    assert cart.subtotal == Decimal("75.70")
    assert cart.item_count == 6


def test_adding_a_product_again_increases_its_quantity() -> None:
    cart = Cart()
    cart.add(TEA, 2)
    cart.add(TEA)
    (line,) = cart.lines
    assert line.quantity == 3
    assert line.net == Decimal("14.70")


def test_a_different_product_with_the_same_sku_is_rejected() -> None:
    cart = Cart()
    cart.add(TEA)
    with pytest.raises(ValueError, match="different product"):
        cart.add(Product("TEA-GREEN", "Black tea", Decimal("5.50")))


@pytest.mark.parametrize("quantity", [0, -1, MAX_QUANTITY + 1])
def test_invalid_quantities(quantity: int) -> None:
    with pytest.raises(ValueError, match="quantity"):
        Cart().add(MUG, quantity)


def test_quantity_must_be_an_integer() -> None:
    with pytest.raises(TypeError):
        Cart().add(MUG, 1.5)  # type: ignore[arg-type]


def test_set_quantity_and_remove(cart: Cart) -> None:
    cart.set_quantity("MUG-STONE", 1)
    assert cart.subtotal == Decimal("57.70")
    cart.set_quantity("TEA-GREEN", 0)
    cart.remove("BOOK-BREW")
    assert [line.product for line in cart.lines] == [MUG]
    with pytest.raises(UnknownProductError):
        cart.remove("BOOK-BREW")
    with pytest.raises(UnknownProductError):
        cart.set_quantity("NOPE", 1)


def test_an_empty_cart() -> None:
    cart = Cart()
    assert cart.is_empty
    assert cart.subtotal == Decimal("0.00")
    cart.add(BOOK)
    assert not cart.is_empty
