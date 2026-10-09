"""Exceptions raised by shopkit.

Every error the library raises on bad input derives from :class:`ShopkitError`, so callers (and
the CLI) can handle all of them in one place.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import ClassVar


class ShopkitError(Exception):
    """Base class for all shopkit errors."""


class InvalidAmountError(ShopkitError, ValueError):
    """A money amount is malformed, negative where it must not be, or too precise."""


class UnknownProductError(ShopkitError, LookupError):
    """A SKU is not in the catalog or the cart."""

    def __init__(self, sku: str) -> None:
        super().__init__(f"unknown product: {sku}")
        self.sku = sku


class CouponError(ShopkitError):
    """A coupon cannot be used. ``reason`` is a short, stable code for programs."""

    MESSAGES: ClassVar[Mapping[str, str]] = {
        "unknown_code": "this coupon code does not exist",
        "expired": "this coupon has expired",
        "below_minimum": "the cart does not reach the coupon's minimum value",
    }

    def __init__(self, reason: str) -> None:
        super().__init__(self.MESSAGES.get(reason, reason))
        self.reason = reason


class CartFileError(ShopkitError):
    """A cart or coupon file cannot be read or does not match the expected format."""
