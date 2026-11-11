"""VAT in whole cents, computed with integer arithmetic only.

This is separate from :mod:`shopkit.vat`, which works in :class:`decimal.Decimal` francs. Use
:func:`vat_amount` when the net amount is already held as an integer number of cents.
"""

from __future__ import annotations


def vat_amount(net_cents: int, rate_percent: int) -> int:
    """The VAT on ``net_cents``, in cents, at ``rate_percent`` per cent, rounded half up.

    The rate is a whole-number percent, so the VAT is ``net_cents * rate_percent / 100``, rounded
    to the nearest cent with exact halves rounded up. For example ``vat_amount(1000, 8) == 80``
    and ``vat_amount(1005, 8) == 80`` (8.04 rounds down), and ``vat_amount(25, 2) == 1`` (0.5
    rounds up). Negative inputs are not specially handled.
    """
    return (net_cents * rate_percent + 50) // 100
