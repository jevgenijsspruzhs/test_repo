from __future__ import annotations

from decimal import Decimal

import pytest

from shopkit.errors import InvalidAmountError
from shopkit.money import format_chf, parse_amount, percent_of, round_cash, round_cents


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("4.90", Decimal("4.90")),
        ("12", Decimal("12.00")),
        (7, Decimal("7.00")),
        (" 3.5 ", Decimal("3.50")),
    ],
)
def test_parse_amount(raw: str | int, expected: Decimal) -> None:
    assert parse_amount(raw) == expected


@pytest.mark.parametrize("raw", ["abc", "1.234", "-1.00", "NaN", "Infinity", ""])
def test_parse_amount_rejects_bad_input(raw: str) -> None:
    with pytest.raises(InvalidAmountError):
        parse_amount(raw)


def test_parse_amount_rejects_floats_and_bools() -> None:
    with pytest.raises(InvalidAmountError):
        parse_amount(4.9)  # type: ignore[arg-type]
    with pytest.raises(InvalidAmountError):
        parse_amount(True)


def test_parse_amount_allows_negative_when_asked() -> None:
    assert parse_amount("-2.50", allow_negative=True) == Decimal("-2.50")


def test_round_cents_rounds_half_up() -> None:
    assert round_cents(Decimal("0.005")) == Decimal("0.01")
    assert round_cents(Decimal("2.344")) == Decimal("2.34")


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        ("12.32", "12.30"),
        ("12.33", "12.35"),
        ("12.37", "12.35"),
        ("12.38", "12.40"),
        ("0.00", "0.00"),
    ],
)
def test_round_cash_to_five_rappen(amount: str, expected: str) -> None:
    assert round_cash(Decimal(amount)) == Decimal(expected)


def test_percent_of() -> None:
    assert percent_of(Decimal("79.70"), Decimal("10")) == Decimal("7.97")
    assert percent_of(Decimal("19.80"), Decimal("15")) == Decimal("2.97")


def test_format_chf_uses_the_swiss_thousands_separator() -> None:
    assert format_chf(Decimal("1234.5")) == "CHF 1'234.50"
    assert format_chf(Decimal("0")) == "CHF 0.00"
