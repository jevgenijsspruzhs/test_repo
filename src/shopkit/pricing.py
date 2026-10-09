"""Pricing a cart: discount, VAT and totals.

The calculation follows a Swiss invoice:

1. the subtotal is the sum of the line nets (prices exclude VAT);
2. a coupon discount is taken off the subtotal and spread across the lines in proportion to
   their nets, so each VAT category is taxed on its discounted amount;
3. VAT is computed per rate on that rate's total taxable amount and rounded once per rate;
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
    result: list[VatLine] = []
    for category in VatCategory:
        in_category = [line for line in lines if line.vat_category is category]
        if not in_category:
            continue
        rate = rates.rate(category)
        taxable = sum((line.taxable for line in in_category), ZERO)
        vat = sum((vat_amount(line.taxable, rate) for line in in_category), ZERO)
        result.append(VatLine(category, rate, taxable, vat))
    return tuple(result)


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
