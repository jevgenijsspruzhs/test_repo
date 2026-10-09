"""Coupon codes: a percentage or a fixed amount off the cart subtotal."""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from shopkit.errors import CouponError, InvalidAmountError
from shopkit.money import ZERO, percent_of

CODE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9-]{2,31}$")


class CouponKind(StrEnum):
    PERCENT = "percent"
    FIXED = "fixed"


@dataclass(frozen=True, slots=True)
class Coupon:
    """A discount code.

    ``value`` is a percentage (``PERCENT``, 0-100) or an amount in CHF (``FIXED``). The discount
    applies to the net subtotal, before VAT.

    ``valid_until`` is the last day on which the coupon can be used (inclusive); ``None`` means it
    never expires. ``min_subtotal`` is the smallest net subtotal the coupon accepts.
    """

    code: str
    kind: CouponKind
    value: Decimal
    valid_until: date | None = None
    min_subtotal: Decimal = ZERO

    def __post_init__(self) -> None:
        if not CODE_PATTERN.match(self.code):
            raise ValueError(f"invalid coupon code {self.code!r}: use A-Z, 0-9 and '-'")
        if self.kind is CouponKind.PERCENT and not Decimal(0) < self.value <= Decimal(100):
            raise InvalidAmountError(f"percentage must be in (0, 100]: {self.value}")
        if self.kind is CouponKind.FIXED and self.value <= 0:
            raise InvalidAmountError(f"fixed discount must be positive: {self.value}")
        if self.min_subtotal < 0:
            raise InvalidAmountError(f"minimum subtotal must not be negative: {self.min_subtotal}")

    def check(self, subtotal: Decimal, today: date) -> None:
        """Raise :class:`CouponError` unless the coupon can be used for this subtotal today."""
        if self.valid_until is not None and today >= self.valid_until:
            raise CouponError("expired")
        if self.min_subtotal and subtotal <= self.min_subtotal:
            raise CouponError("below_minimum")

    def discount_for(self, subtotal: Decimal) -> Decimal:
        """The discount in CHF for a net subtotal (call :meth:`check` first)."""
        if self.kind is CouponKind.PERCENT:
            return percent_of(subtotal, self.value)
        return self.value


class CouponBook:
    """The coupons a shop accepts, by code."""

    def __init__(self, coupons: Iterable[Coupon] = ()) -> None:
        self._by_code: dict[str, Coupon] = {}
        for coupon in coupons:
            if coupon.code in self._by_code:
                raise ValueError(f"duplicate coupon code: {coupon.code}")
            self._by_code[coupon.code] = coupon

    def find(self, code: str) -> Coupon:
        """The coupon for a code as a customer typed it."""
        try:
            return self._by_code[code]
        except KeyError:
            raise CouponError("unknown_code") from None

    def __iter__(self) -> Iterator[Coupon]:
        return iter(self._by_code.values())

    def __len__(self) -> int:
        return len(self._by_code)
