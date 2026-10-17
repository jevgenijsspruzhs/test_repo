"""Pricing a cart: discount, VAT and totals.

The calculation follows a Swiss invoice:

1. the subtotal is the sum of the line nets (prices exclude VAT);
2. a coupon discount is taken off the subtotal and spread across the lines in proportion to
   their nets, so each VAT category is taxed on its discounted amount;
3. VAT is computed once per rate, on the total taxable amount of the lines at that rate, and
   rounded half up to the cent. It is not computed per line, so cheap items do not accumulate
   rounding differences. Each VAT category gets its own :class:`VatLine`; with the Swiss rates
   every category has a rate of its own, and categories that share a rate split that rate's VAT
   in proportion to their taxable amounts;
4. the total is the discounted subtotal plus VAT; the cash total is rounded to 5 Rappen.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from shopkit.cart import Cart
from shopkit.coupons import Coupon
from shopkit.money import ZERO, round_cash, round_cents
from shopkit.vat import SWISS_RATES, VatCategory, VatRates, vat_amount


@dataclass(frozen=True, slots=True)
class QuoteLine:
    sku: str
    name: str
    quantity: int
    unit_price: Decimal
    net: Decimal
    discount: Decimal
    vat_category: VatCategory

    @property
    def taxable(self) -> Decimal:
        return self.net - self.discount


@dataclass(frozen=True, slots=True)
class VatLine:
    category: VatCategory
    rate: Decimal
    taxable: Decimal
    vat: Decimal


@dataclass(frozen=True, slots=True)
class Quote:
    lines: tuple[QuoteLine, ...]
    subtotal: Decimal
    coupon_code: str | None
    discount: Decimal
    vat_lines: tuple[VatLine, ...]

    @property
    def vat_total(self) -> Decimal:
        return sum((line.vat for line in self.vat_lines), ZERO)

    @property
    def total(self) -> Decimal:
        return self.subtotal - self.discount + self.vat_total

    @property
    def cash_total(self) -> Decimal:
        return round_cash(self.total)


def allocate(amount: Decimal, weights: Sequence[Decimal]) -> list[Decimal]:
    """Split ``amount`` across ``weights`` proportionally, in cents.

    The rounding remainder goes to the largest weight (the first one, on a tie), so the parts
    always add up to ``amount`` exactly.
    """
    if not weights:
        return []
    total = sum(weights, ZERO)
    if total == 0:
        return [ZERO for _ in weights]
    parts = [round_cents(amount * weight / total) for weight in weights]
    largest = max(range(len(weights)), key=lambda index: weights[index])
    parts[largest] += amount - sum(parts, ZERO)
    return parts


def _vat_lines(lines: Sequence[QuoteLine], rates: VatRates) -> tuple[VatLine, ...]:
    """One line per VAT category in use. VAT is computed once per rate, on the rate's total.

    Categories that share a rate (possible with custom :class:`VatRates`) have that rate's VAT
    split between them in proportion to their taxable amounts, so the cents still add up.
    """
    categories = [c for c in VatCategory if any(line.vat_category is c for line in lines)]
    taxable = {
        category: sum(
            (line.taxable for line in lines if line.vat_category is category),
            ZERO,
        )
        for category in categories
    }
    by_rate: dict[Decimal, list[VatCategory]] = {}
    for category in categories:
        by_rate.setdefault(rates.rate(category), []).append(category)
    vat: dict[VatCategory, Decimal] = {}
    for rate, group in by_rate.items():
        rate_vat = vat_amount(sum((taxable[c] for c in group), ZERO), rate)
        vat.update(zip(group, allocate(rate_vat, [taxable[c] for c in group]), strict=True))
    return tuple(
        VatLine(category, rates.rate(category), taxable[category], vat[category])
        for category in categories
    )


def quote(
    cart: Cart,
    *,
    today: date,
    coupon: Coupon | None = None,
    rates: VatRates = SWISS_RATES,
) -> Quote:
    """Price ``cart``. Raises :class:`~shopkit.errors.CouponError` if the coupon is not valid."""
    subtotal = cart.subtotal
    discount = ZERO
    if coupon is not None:
        coupon.check(subtotal, today)
        discount = coupon.discount_for(subtotal)
    shares = allocate(discount, [line.net for line in cart.lines])
    lines = tuple(
        QuoteLine(
            sku=line.product.sku,
            name=line.product.name,
            quantity=line.quantity,
            unit_price=line.product.unit_price,
            net=line.net,
            discount=share,
            vat_category=line.product.vat_category,
        )
        for line, share in zip(cart.lines, shares, strict=True)
    )
    return Quote(
        lines=lines,
        subtotal=subtotal,
        coupon_code=None if coupon is None else coupon.code,
        discount=discount,
        vat_lines=_vat_lines(lines, rates),
    )
