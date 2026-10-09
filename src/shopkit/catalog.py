"""Products and the catalog they come from."""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from decimal import Decimal

from shopkit.errors import InvalidAmountError, UnknownProductError
from shopkit.vat import VatCategory

SKU_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9-]{1,31}$")
MAX_NAME_LENGTH = 80


@dataclass(frozen=True, slots=True)
class Product:
    """A product that can be sold. ``unit_price`` is net (excluding VAT), in CHF."""

    sku: str
    name: str
    unit_price: Decimal
    vat_category: VatCategory = VatCategory.STANDARD

    def __post_init__(self) -> None:
        if not SKU_PATTERN.match(self.sku):
            raise ValueError(f"invalid SKU {self.sku!r}: use A-Z, 0-9 and '-' (2-32 characters)")
        if not self.name.strip() or len(self.name) > MAX_NAME_LENGTH:
            raise ValueError(f"product name must be 1-{MAX_NAME_LENGTH} characters")
        if self.unit_price < 0:
            raise InvalidAmountError(f"unit price must not be negative: {self.unit_price}")


class Catalog:
    """Products by SKU."""

    def __init__(self, products: Iterable[Product] = ()) -> None:
        self._products: dict[str, Product] = {}
        for product in products:
            self.add(product)

    def add(self, product: Product) -> None:
        if product.sku in self._products:
            raise ValueError(f"duplicate SKU: {product.sku}")
        self._products[product.sku] = product

    def get(self, sku: str) -> Product:
        try:
            return self._products[sku]
        except KeyError:
            raise UnknownProductError(sku) from None

    def __contains__(self, sku: object) -> bool:
        return sku in self._products

    def __iter__(self) -> Iterator[Product]:
        return iter(self._products.values())

    def __len__(self) -> int:
        return len(self._products)
