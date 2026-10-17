from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from shopkit.cart import Cart
from shopkit.catalog import Product
from shopkit.pricing import quote
from shopkit.vat import SWISS_RATES, VatCategory, VatRates, parse_category, vat_amount

TODAY = date(2026, 10, 1)


def test_swiss_rates() -> None:
    assert SWISS_RATES.rate(VatCategory.STANDARD) == Decimal("8.1")
    assert SWISS_RATES.rate(VatCategory.REDUCED) == Decimal("2.6")
    assert SWISS_RATES.rate(VatCategory.ACCOMMODATION) == Decimal("3.8")
    assert SWISS_RATES.rate(VatCategory.EXEMPT) == Decimal("0")


def test_vat_amount_rounds_to_the_cent() -> None:
    assert vat_amount(Decimal("100.00"), Decimal("8.1")) == Decimal("8.10")
    assert vat_amount(Decimal("32.40"), Decimal("8.1")) == Decimal("2.62")


def test_vat_amount_rounds_half_up_not_to_even() -> None:
    assert vat_amount(Decimal("0.25"), Decimal("10")) == Decimal("0.03")  # 0.025
    assert vat_amount(Decimal("0.05"), Decimal("50")) == Decimal("0.03")  # 0.025


def test_three_cheap_items_pay_vat_once_on_their_total() -> None:
    # Three different products at CHF 0.10, same rate: 0.30 * 8.1 % = 0.0243 -> 0.02.
    # Rounding each item first would give 3 x 0.01 = 0.03.
    cart = Cart()
    for sku in ("PEN-BLUE", "PEN-RED", "PEN-BLACK"):
        cart.add(Product(sku, "Ballpoint pen", Decimal("0.10"), VatCategory.STANDARD))
    result = quote(cart, today=TODAY)
    (vat,) = result.vat_lines
    assert vat.taxable == Decimal("0.30")
    assert vat.vat == Decimal("0.02")
    assert result.total == Decimal("0.32")


def test_custom_rates_must_cover_every_category() -> None:
    with pytest.raises(ValueError, match="missing"):
        VatRates({VatCategory.STANDARD: Decimal("7.7")})


def test_rates_must_be_in_range() -> None:
    rates = dict(SWISS_RATES.rates)
    rates[VatCategory.STANDARD] = Decimal("120")
    with pytest.raises(ValueError, match="out of range"):
        VatRates(rates)


def test_parse_category() -> None:
    assert parse_category(" Reduced ") is VatCategory.REDUCED
    with pytest.raises(ValueError, match="unknown VAT category"):
        parse_category("luxury")
