from __future__ import annotations

from decimal import Decimal

import pytest

from shopkit.vat import SWISS_RATES, VatCategory, VatRates, parse_category, vat_amount
from shopkit.vat_cents import vat_amount as vat_amount_cents


def test_swiss_rates() -> None:
    assert SWISS_RATES.rate(VatCategory.STANDARD) == Decimal("8.1")
    assert SWISS_RATES.rate(VatCategory.REDUCED) == Decimal("2.6")
    assert SWISS_RATES.rate(VatCategory.ACCOMMODATION) == Decimal("3.8")
    assert SWISS_RATES.rate(VatCategory.EXEMPT) == Decimal("0")


def test_vat_amount_rounds_to_the_cent() -> None:
    assert vat_amount(Decimal("100.00"), Decimal("8.1")) == Decimal("8.10")
    assert vat_amount(Decimal("32.40"), Decimal("8.1")) == Decimal("2.62")


def test_vat_amount_rounds_half_up() -> None:
    assert vat_amount(Decimal("12.50"), Decimal("1")) == Decimal("0.13")  # 0.125 -> 0.13


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


def test_vat_of_a_fully_discounted_amount_is_zero() -> None:
    assert vat_amount(Decimal("0.00"), Decimal("8.1")) == Decimal("0.00")
    assert vat_amount(Decimal("0.00"), Decimal("2.6")) == Decimal("0.00")


def test_vat_amount_cents_examples_from_the_ticket() -> None:
    assert vat_amount_cents(1000, 8) == 80
    assert vat_amount_cents(1005, 8) == 80


def test_vat_amount_cents_exact_half_cent_rounds_up() -> None:
    assert vat_amount_cents(25, 2) == 1  # 0.50 -> 1
    assert vat_amount_cents(5, 10) == 1  # 0.50 -> 1


def test_vat_amount_cents_just_below_half_cent_rounds_down() -> None:
    assert vat_amount_cents(24, 2) == 0  # 0.48 -> 0
    assert vat_amount_cents(1004, 8) == 80  # 80.32 -> 80


def test_vat_amount_cents_zero_net_amount_has_no_vat() -> None:
    assert vat_amount_cents(0, 8) == 0


def test_vat_amount_cents_zero_rate_has_no_vat() -> None:
    assert vat_amount_cents(1000, 0) == 0
