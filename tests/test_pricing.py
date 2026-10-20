from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from shopkit.cart import Cart
from shopkit.catalog import Product
from shopkit.coupons import Coupon, CouponKind
from shopkit.errors import CouponError
from shopkit.pricing import VatLine, allocate, quote
from shopkit.vat import SWISS_RATES, VatCategory, VatRates
from tests.conftest import LAMP, MUG

TODAY = date(2026, 10, 1)


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


CHEAP = Product("PIN-CHEAP", "Pin", Decimal("0.10"), VatCategory.STANDARD)
CHEAP_REDUCED = Product("PIN-REDUCED", "Reduced pin", Decimal("0.10"), VatCategory.REDUCED)


def test_vat_is_computed_once_per_rate_not_per_line() -> None:
    # Three items at CHF 0.10: 0.30 * 8.1 % = 0.0243 -> 0.02. Per line it would be 3 x 0.01 = 0.03.
    cart = Cart()
    cart.add(CHEAP, 3)
    result = quote(cart, today=TODAY)
    assert result.vat_lines == (
        VatLine(VatCategory.STANDARD, Decimal("8.1"), Decimal("0.30"), Decimal("0.02")),
    )
    assert result.vat_total == Decimal("0.02")
    assert result.total == Decimal("0.32")


def test_vat_lines_group_by_rate() -> None:
    cart = Cart()
    cart.add(CHEAP, 3)
    cart.add(CHEAP_REDUCED, 3)
    result = quote(cart, today=TODAY)
    # Standard: 0.30 * 8.1 % = 0.0243 -> 0.02. Reduced: 0.30 * 2.6 % = 0.0078 -> 0.01.
    assert result.vat_lines == (
        VatLine(VatCategory.STANDARD, Decimal("8.1"), Decimal("0.30"), Decimal("0.02")),
        VatLine(VatCategory.REDUCED, Decimal("2.6"), Decimal("0.30"), Decimal("0.01")),
    )
    assert result.vat_total == Decimal("0.03")


def test_a_gift_coupon_larger_than_the_cart_is_capped_at_the_subtotal() -> None:
    # Regression: a CHF 50 coupon on a CHF 30 cart gave a total of -CHF 21.62 and negative VAT.
    cart = Cart()
    cart.add(Product("GIFT-BOX", "Gift box", Decimal("30.00"), VatCategory.STANDARD))
    coupon = Coupon("GIFT50", CouponKind.FIXED, Decimal("50.00"))
    result = quote(cart, today=TODAY, coupon=coupon)
    assert result.discount == Decimal("30.00")
    assert result.total == Decimal("0.00")
    assert result.cash_total == Decimal("0.00")
    assert all(line.taxable == Decimal("0.00") for line in result.lines)
    assert all(vat.taxable >= 0 and vat.vat >= 0 for vat in result.vat_lines)
    assert result.vat_total == Decimal("0.00")
