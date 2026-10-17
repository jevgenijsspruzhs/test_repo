from __future__ import annotations

from decimal import Decimal

import pytest

from shopkit.vat import SWISS_RATES, VatCategory, VatRates, parse_category, vat_amount


def test_swiss_rates() -> None:
    assert SWISS_RATES.rate(VatCategory.STANDARD) == Decimal("8.1")
    assert SWISS_RATES.rate(VatCategory.REDUCED) == Decimal("2.6")
    assert SWISS_RATES.rate(VatCategory.ACCOMMODATION) == Decimal("3.8")
    assert SWISS_RATES.rate(VatCategory.EXEMPT) == Decimal("0")


def test_vat_amount_rounds_to_the_cent() -> None:
    assert vat_amount(Decimal("100.00"), Decimal("8.1")) == Decimal("8.10")
    assert vat_amount(Decimal("32.40"), Decimal("8.1")) == Decimal("2.62")


def test_vat_of_three_cheap_items_is_computed_on_their_total() -> None:
    # Regression: three items at CHF 0.10 are 0.30 net. 8.1 % of 0.30 is 0.0243, so CHF 0.02.
    assert vat_amount(Decimal("0.30"), Decimal("8.1")) == Decimal("0.02")


def test_vat_amount_rounds_half_up() -> None:
    assert vat_amount(Decimal("0.05"), Decimal("10")) == Decimal("0.01")
    assert vat_amount(Decimal("0.25"), Decimal("10")) == Decimal("0.03")


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
