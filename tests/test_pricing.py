from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from shopkit.cart import Cart
from shopkit.catalog import Product
from shopkit.coupons import Coupon, CouponKind
from shopkit.errors import CouponError
from shopkit.pricing import allocate, quote
from shopkit.vat import SWISS_RATES, VatCategory, VatRates
from tests.conftest import LAMP, MUG

TODAY = date(2026, 10, 1)
SWEET_A = Product("SWEET-A", "Sweet A", Decimal("0.10"), VatCategory.STANDARD)
SWEET_B = Product("SWEET-B", "Sweet B", Decimal("0.10"), VatCategory.STANDARD)
SWEET_C = Product("SWEET-C", "Sweet C", Decimal("0.10"), VatCategory.STANDARD)
BISCUIT = Product("BISCUIT", "Biscuit", Decimal("0.10"), VatCategory.REDUCED)


def test_quote_without_coupon(cart: Cart) -> None:
    result = quote(cart, today=TODAY)
    assert result.subtotal == Decimal("75.70")
    assert result.discount == Decimal("0.00")
    assert result.coupon_code is None
    vat = {line.category: (line.taxable, line.vat) for line in result.vat_lines}
    assert vat == {
        VatCategory.STANDARD: (Decimal("36.00"), Decimal("2.92")),
        VatCategory.REDUCED: (Decimal("39.70"), Decimal("1.03")),
    }
    assert result.total == Decimal("79.65")
    assert result.cash_total == Decimal("79.65")


def test_quote_with_a_percentage_coupon(cart: Cart) -> None:
    coupon = Coupon("WELCOME10", CouponKind.PERCENT, Decimal("10"), min_subtotal=Decimal("20.00"))
    result = quote(cart, today=TODAY, coupon=coupon)
    assert result.discount == Decimal("7.57")
    assert [line.discount for line in result.lines] == [
        Decimal("1.47"),
        Decimal("3.60"),
        Decimal("2.50"),
    ]
    assert [line.taxable for line in result.lines] == [
        Decimal("13.23"),
        Decimal("32.40"),
        Decimal("22.50"),
    ]
    assert result.vat_total == Decimal("3.55")
    assert result.total == Decimal("71.68")


def test_quote_with_a_fixed_coupon() -> None:
    cart = Cart()
    cart.add(LAMP)
    result = quote(cart, today=TODAY, coupon=Coupon("FIVEOFF", CouponKind.FIXED, Decimal("5.00")))
    assert result.total == Decimal("59.46")  # 55.00 + 8.1 % VAT (4.455 -> 4.46)


def test_an_invalid_coupon_stops_the_quote(cart: Cart) -> None:
    coupon = Coupon("BIGSPEND", CouponKind.FIXED, Decimal("10.00"), min_subtotal=Decimal("500.00"))
    with pytest.raises(CouponError):
        quote(cart, today=TODAY, coupon=coupon)


def test_custom_vat_rates(cart: Cart) -> None:
    rates = dict(SWISS_RATES.rates)
    rates[VatCategory.STANDARD] = Decimal("10")
    result = quote(cart, today=TODAY, rates=VatRates(rates))
    standard = next(v for v in result.vat_lines if v.category is VatCategory.STANDARD)
    assert standard.vat == Decimal("3.60")


def test_an_empty_cart_has_a_zero_quote() -> None:
    result = quote(Cart(), today=TODAY)
    assert result.lines == ()
    assert result.vat_lines == ()
    assert result.total == Decimal("0.00")


def test_single_category_cart() -> None:
    cart = Cart()
    cart.add(MUG, 3)
    result = quote(cart, today=TODAY)
    assert [v.category for v in result.vat_lines] == [VatCategory.STANDARD]
    assert result.total == Decimal("58.37")  # 54.00 + 4.374 -> 4.37


@pytest.mark.parametrize(
    ("amount", "weights", "expected"),
    [
        ("10.00", ["30", "70"], ["3.00", "7.00"]),
        ("0.10", ["1", "1", "1"], ["0.04", "0.03", "0.03"]),
        ("1.00", ["1", "2"], ["0.33", "0.67"]),
        ("5.00", ["0", "0"], ["0.00", "0.00"]),
    ],
)
def test_allocate_always_adds_up(amount: str, weights: list[str], expected: list[str]) -> None:
    parts = allocate(Decimal(amount), [Decimal(w) for w in weights])
    assert parts == [Decimal(e) for e in expected]
    if any(Decimal(w) for w in weights):
        assert sum(parts) == Decimal(amount)


def test_allocate_nothing() -> None:
    assert allocate(Decimal("1.00"), []) == []


def test_three_cheap_items_pay_vat_once_on_their_total() -> None:
    # 3 x 0.10 = 0.30 at 8.1 % is 0.0243, which rounds to 0.02. Rounding each item first
    # (0.0081 -> 0.01, three times) would give 0.03.
    cart = Cart()
    cart.add(SWEET_A)
    cart.add(SWEET_B)
    cart.add(SWEET_C)
    result = quote(cart, today=TODAY)
    assert [(v.category, v.taxable, v.vat) for v in result.vat_lines] == [
        (VatCategory.STANDARD, Decimal("0.30"), Decimal("0.02")),
    ]
    assert result.vat_total == Decimal("0.02")
    assert result.total == Decimal("0.32")


def test_three_cheap_items_of_one_sku_pay_vat_once_on_their_total() -> None:
    cart = Cart()
    cart.add(SWEET_A, 3)
    result = quote(cart, today=TODAY)
    assert result.vat_total == Decimal("0.02")


def test_each_vat_rate_is_rounded_separately() -> None:
    # Standard: 0.30 * 8.1 % = 0.0243 -> 0.02. Reduced: 0.30 * 2.6 % = 0.0078 -> 0.01.
    cart = Cart()
    cart.add(SWEET_A, 3)
    cart.add(BISCUIT, 3)
    result = quote(cart, today=TODAY)
    vat = {line.category: line.vat for line in result.vat_lines}
    assert vat == {VatCategory.STANDARD: Decimal("0.02"), VatCategory.REDUCED: Decimal("0.01")}
    assert result.vat_total == Decimal("0.03")


def test_coupon_discount_is_taken_before_vat_per_rate() -> None:
    cart = Cart()
    cart.add(SWEET_A, 3)
    cart.add(SWEET_B, 3)
    cart.add(BISCUIT, 3)
    coupon = Coupon("TENOFF", CouponKind.PERCENT, Decimal("10"))
    result = quote(cart, today=TODAY, coupon=coupon)
    assert result.subtotal == Decimal("0.90")
    assert result.discount == Decimal("0.09")
    vat = {line.category: (line.taxable, line.vat) for line in result.vat_lines}
    # Standard: 0.54 * 8.1 % = 0.04374 -> 0.04. Reduced: 0.27 * 2.6 % = 0.00702 -> 0.01.
    assert vat == {
        VatCategory.STANDARD: (Decimal("0.54"), Decimal("0.04")),
        VatCategory.REDUCED: (Decimal("0.27"), Decimal("0.01")),
    }
    assert result.total == result.subtotal - result.discount + result.vat_total
    assert result.total == Decimal("0.86")
