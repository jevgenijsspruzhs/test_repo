"""shopkit: a small e-commerce domain library (products, cart, coupons, Swiss VAT)."""

from shopkit.cart import Cart, LineItem, cart_item_count
from shopkit.catalog import Catalog, Product
from shopkit.coupons import Coupon, CouponBook, CouponKind
from shopkit.errors import (
    CartFileError,
    CouponError,
    InvalidAmountError,
    ShopkitError,
    UnknownProductError,
)
from shopkit.pricing import Quote, quote
from shopkit.vat import SWISS_RATES, VatCategory, VatRates

__version__ = "0.3.0"

__all__ = [
    "SWISS_RATES",
    "Cart",
    "CartFileError",
    "Catalog",
    "Coupon",
    "CouponBook",
    "CouponError",
    "CouponKind",
    "InvalidAmountError",
    "LineItem",
    "Product",
    "Quote",
    "ShopkitError",
    "UnknownProductError",
    "VatCategory",
    "VatRates",
    "__version__",
    "cart_item_count",
    "quote",
]
