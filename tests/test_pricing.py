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


def _cheap(sku: str, category: VatCategory = VatCategory.STANDARD) -> Product:
    return Product(sku, f"Paper clip {sku}", Decimal("0.10"), category)


def test_vat_is_computed_once_per_rate_not_per_item() -> None:
    # Regression: three different items at CHF 0.10 are 0.30 net in total. 8.1 % of 0.30 is
    # 0.0243, so the VAT is CHF 0.02. Rounding each 0.0081 line first would give CHF 0.03.
    cart = Cart()
    for sku in ("CLIP-A", "CLIP-B", "CLIP-C"):
        cart.add(_cheap(sku))
    result = quote(cart, today=TODAY)
    assert result.subtotal == Decimal("0.30")
    assert result.vat_total == Decimal("0.02")
    assert result.total == Decimal("0.32")


def test_vat_is_rounded_half_up_on_the_rate_total() -> None:
    rates = VatRates({**SWISS_RATES.rates, VatCategory.STANDARD: Decimal("10")})
    cart = Cart()
    cart.add(Product("HALF-A", "Half cent A", Decimal("0.05"), VatCategory.STANDARD))
    cart.add(Product("HALF-B", "Half cent B", Decimal("0.20"), VatCategory.STANDARD))
    result = quote(cart, today=TODAY, rates=rates)
    # 0.25 at 10 % is 0.025, which rounds half up to 0.03 (half even would give 0.02).
    assert result.vat_total == Decimal("0.03")


def test_each_rate_is_rounded_separately_in_a_mixed_cart() -> None:
    cart = Cart()
    for sku in ("CLIP-A", "CLIP-B", "CLIP-C"):
        cart.add(_cheap(sku))  # standard: 0.30 at 8.1 % -> 0.02
    for sku in ("TEA-A", "TEA-B", "TEA-C"):
        cart.add(_cheap(sku, VatCategory.REDUCED))  # reduced: 0.30 at 2.6 % -> 0.0078 -> 0.01
    result = quote(cart, today=TODAY)
    vat = {line.category: line.vat for line in result.vat_lines}
    assert vat == {VatCategory.STANDARD: Decimal("0.02"), VatCategory.REDUCED: Decimal("0.01")}
    assert result.vat_total == Decimal("0.03")


def test_coupon_is_taken_off_the_net_before_vat() -> None:
    cart = Cart()
    for sku in ("CLIP-A", "CLIP-B", "CLIP-C"):
        cart.add(_cheap(sku))
    cart.add(MUG, 1)  # 18.00 standard, so the standard total is 18.30
    coupon = Coupon("FIVEPERCENT", CouponKind.PERCENT, Decimal("5"))
    result = quote(cart, today=TODAY, coupon=coupon)
    # 5 % of 18.30 is 0.915, rounded to 0.92; the discount leaves 17.38 at the standard rate
    assert result.discount == Decimal("0.92")
    standard = next(v for v in result.vat_lines if v.category is VatCategory.STANDARD)
    assert standard.taxable == Decimal("17.38")
    # 17.38 at 8.1 % = 1.40778 -> 1.41
    assert standard.vat == Decimal("1.41")
