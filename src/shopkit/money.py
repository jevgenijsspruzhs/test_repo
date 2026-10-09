"""Money helpers.

All amounts are :class:`decimal.Decimal` values in Swiss francs (CHF); shopkit never uses
``float`` for money. Rounding is always explicit:

* amounts are rounded to the cent (0.01) using ``ROUND_HALF_UP``;
* cash totals are rounded to 5 Rappen (0.05), also half up, as Swiss cash payments require.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from shopkit.errors import InvalidAmountError

CENT = Decimal("0.01")
FIVE_RAPPEN = Decimal("0.05")
ZERO = Decimal("0.00")


def parse_amount(value: str | int | Decimal, *, allow_negative: bool = False) -> Decimal:
    """Parse an amount from configuration or JSON.

    Strings, integers and decimals are accepted; floats are rejected because most amounts
    cannot be represented exactly. More than two decimal places is an error rather than being
    silently rounded away.
    """
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        raise InvalidAmountError(f"amount must be a string or an integer, not {value!r}")
    try:
        amount = Decimal(value.strip()) if isinstance(value, str) else Decimal(value)
    except InvalidOperation:
        raise InvalidAmountError(f"not a valid amount: {value!r}") from None
    if not amount.is_finite():
        raise InvalidAmountError(f"not a valid amount: {value!r}")
    if amount != amount.quantize(CENT):
        raise InvalidAmountError(f"amount has more than two decimal places: {value!r}")
    if amount < 0 and not allow_negative:
        raise InvalidAmountError(f"amount must not be negative: {value!r}")
    return amount.quantize(CENT)


def round_cents(amount: Decimal) -> Decimal:
    """Round to the cent, half up."""
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


def round_cash(amount: Decimal) -> Decimal:
    """Round to 5 Rappen, half up (12.32 -> 12.30, 12.33 -> 12.35)."""
    steps = (amount / FIVE_RAPPEN).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    return (steps * FIVE_RAPPEN).quantize(CENT)


def percent_of(amount: Decimal, percent: Decimal) -> Decimal:
    """``percent`` per cent of ``amount``, rounded to the cent (half up)."""
    return round(amount * percent / 100, 2)


def format_chf(amount: Decimal) -> str:
    """Format for people: ``CHF 1'234.50`` (Swiss thousands separator)."""
    return "CHF " + f"{amount:,.2f}".replace(",", "'")
