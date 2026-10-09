"""The shopping cart."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from shopkit.catalog import Product
from shopkit.errors import UnknownProductError
from shopkit.money import ZERO

MAX_QUANTITY = 999


@dataclass(frozen=True, slots=True)
class LineItem:
    product: Product
    quantity: int

    @property
    def net(self) -> Decimal:
        """Unit price times quantity, excluding VAT."""
        return self.product.unit_price * self.quantity


def _check_quantity(quantity: int, *, allow_zero: bool) -> None:
    if isinstance(quantity, bool) or not isinstance(quantity, int):
        raise TypeError(f"quantity must be an integer, not {quantity!r}")
    lowest = 0 if allow_zero else 1
    if not lowest <= quantity <= MAX_QUANTITY:
        raise ValueError(f"quantity must be between {lowest} and {MAX_QUANTITY}: {quantity}")


class Cart:
    """Line items in the order they were first added; one line per SKU."""

    def __init__(self) -> None:
        self._lines: dict[str, LineItem] = {}

    def add(self, product: Product, quantity: int = 1) -> None:
        """Add ``quantity`` of a product; adding a product again increases its quantity."""
        _check_quantity(quantity, allow_zero=False)
        current = self._lines.get(product.sku)
        if current is not None:
            if current.product != product:
                raise ValueError(f"a different product with SKU {product.sku} is in the cart")
            quantity += current.quantity
            _check_quantity(quantity, allow_zero=False)
        self._lines[product.sku] = LineItem(product, quantity)

    def set_quantity(self, sku: str, quantity: int) -> None:
        """Change a line's quantity; 0 removes the line."""
        _check_quantity(quantity, allow_zero=True)
        line = self._lines.get(sku)
        if line is None:
            raise UnknownProductError(sku)
        if quantity == 0:
            del self._lines[sku]
        else:
            self._lines[sku] = LineItem(line.product, quantity)

    def remove(self, sku: str) -> None:
        if self._lines.pop(sku, None) is None:
            raise UnknownProductError(sku)

    @property
    def lines(self) -> tuple[LineItem, ...]:
        return tuple(self._lines.values())

    @property
    def is_empty(self) -> bool:
        return not self._lines

    @property
    def item_count(self) -> int:
        return sum(line.quantity for line in self._lines.values())

    @property
    def subtotal(self) -> Decimal:
        """The sum of all line nets, excluding VAT and discounts."""
        return sum((line.net for line in self._lines.values()), ZERO)
