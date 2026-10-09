"""Value added tax (VAT, German: MWST).

Rates are plain configuration: :data:`SWISS_RATES` holds the Swiss rates in force since
1 January 2024. Pass a different :class:`VatRates` to price with other rates.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from types import MappingProxyType

from shopkit.money import round_cents


class VatCategory(StrEnum):
    STANDARD = "standard"
    REDUCED = "reduced"  # food, books, medicine
    ACCOMMODATION = "accommodation"
    EXEMPT = "exempt"


@dataclass(frozen=True, slots=True)
class VatRates:
    """VAT rates in per cent, one per category."""

    rates: Mapping[VatCategory, Decimal]

    def __post_init__(self) -> None:
        missing = set(VatCategory) - set(self.rates)
        if missing:
            names = ", ".join(sorted(category.value for category in missing))
            raise ValueError(f"VAT rates missing for: {names}")
        for category, rate in self.rates.items():
            if not Decimal(0) <= rate < Decimal(100):
                raise ValueError(f"VAT rate for {category.value} out of range: {rate}")
        object.__setattr__(self, "rates", MappingProxyType(dict(self.rates)))

    def rate(self, category: VatCategory) -> Decimal:
        return self.rates[category]


SWISS_RATES = VatRates(
    {
        VatCategory.STANDARD: Decimal("8.1"),
        VatCategory.REDUCED: Decimal("2.6"),
        VatCategory.ACCOMMODATION: Decimal("3.8"),
        VatCategory.EXEMPT: Decimal("0"),
    }
)


def vat_amount(net: Decimal, rate_percent: Decimal) -> Decimal:
    """The VAT on a net amount, rounded to the cent."""
    return round_cents(net * rate_percent / 100)


def parse_category(value: str) -> VatCategory:
    try:
        return VatCategory(value.strip().lower())
    except ValueError:
        allowed = ", ".join(category.value for category in VatCategory)
        raise ValueError(f"unknown VAT category {value!r} (expected one of: {allowed})") from None
