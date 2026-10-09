from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from shopkit.coupons import Coupon, CouponBook, CouponKind
from shopkit.errors import CouponError, InvalidAmountError

TODAY = date(2026, 10, 1)
WELCOME = Coupon(
    "WELCOME10",
    CouponKind.PERCENT,
    Decimal("10"),
    valid_until=date(2026, 12, 31),
    min_subtotal=Decimal("20.00"),
)
FIVE_OFF = Coupon("FIVEOFF", CouponKind.FIXED, Decimal("5.00"))


def test_percentage_discount() -> None:
    assert WELCOME.discount_for(Decimal("79.70")) == Decimal("7.97")


def test_fixed_discount() -> None:
    assert FIVE_OFF.discount_for(Decimal("79.70")) == Decimal("5.00")


def test_a_valid_coupon_passes_the_check() -> None:
    WELCOME.check(Decimal("79.70"), TODAY)
    FIVE_OFF.check(Decimal("0.50"), date(2099, 1, 1))  # no expiry, no minimum


def test_an_expired_coupon_is_rejected() -> None:
    with pytest.raises(CouponError) as excinfo:
        WELCOME.check(Decimal("79.70"), date(2027, 1, 15))
    assert excinfo.value.reason == "expired"


def test_a_cart_below_the_minimum_is_rejected() -> None:
    with pytest.raises(CouponError) as excinfo:
        WELCOME.check(Decimal("19.99"), TODAY)
    assert excinfo.value.reason == "below_minimum"
    assert "minimum" in str(excinfo.value)


@pytest.mark.parametrize("code", ["", "AB", "welcome10", "WELCOME 10", "X" * 33])
def test_invalid_codes(code: str) -> None:
    with pytest.raises(ValueError, match="invalid coupon code"):
        Coupon(code, CouponKind.FIXED, Decimal("1.00"))


@pytest.mark.parametrize(
    ("kind", "value"),
    [(CouponKind.PERCENT, "0"), (CouponKind.PERCENT, "100.01"), (CouponKind.FIXED, "0.00")],
)
def test_invalid_values(kind: CouponKind, value: str) -> None:
    with pytest.raises(InvalidAmountError):
        Coupon("CODE1", kind, Decimal(value))


def test_find_by_code() -> None:
    book = CouponBook([WELCOME, FIVE_OFF])
    assert book.find("FIVEOFF") is FIVE_OFF
    assert len(book) == 2
    assert list(book) == [WELCOME, FIVE_OFF]


def test_unknown_code() -> None:
    with pytest.raises(CouponError) as excinfo:
        CouponBook([WELCOME]).find("NOPE")
    assert excinfo.value.reason == "unknown_code"


def test_duplicate_codes_are_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate coupon code"):
        CouponBook([FIVE_OFF, FIVE_OFF])
