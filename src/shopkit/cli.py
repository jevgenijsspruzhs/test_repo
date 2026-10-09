"""Command line interface: ``python -m shopkit quote cart.json``."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from shopkit import __version__
from shopkit.coupons import Coupon, CouponBook
from shopkit.errors import ShopkitError
from shopkit.loader import load_cart, load_coupons
from shopkit.money import format_chf
from shopkit.pricing import Quote, quote

EXIT_OK = 0
EXIT_ERROR = 2


def _date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a date (YYYY-MM-DD): {value!r}") from None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="shopkit", description="Price shopping carts.")
    parser.add_argument("--version", action="version", version=f"shopkit {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    quote_cmd = commands.add_parser("quote", help="print a priced quote for a cart file")
    quote_cmd.add_argument("cart", type=Path, help="cart JSON file")
    quote_cmd.add_argument("--coupons", type=Path, help="coupon JSON file")
    quote_cmd.add_argument("--coupon", help="coupon code (overrides the cart file's coupon)")
    quote_cmd.add_argument("--today", type=_date, help="pricing date (default: today)")
    quote_cmd.add_argument("--json", action="store_true", help="machine-readable output")
    return parser


def render(result: Quote) -> str:
    """A plain-text quote, one row per line item."""
    width = max(len(line.name) for line in result.lines)
    rows = [
        f"{line.quantity:>3} x {line.name:<{width}}  {format_chf(line.net):>14}"
        for line in result.lines
    ]
    label_width = width + 6

    def total_row(label: str, amount_text: str) -> str:
        return f"{label:<{label_width}}  {amount_text:>14}"

    rows.append(total_row("Subtotal", format_chf(result.subtotal)))
    if result.coupon_code is not None:
        rows.append(total_row(f"Coupon {result.coupon_code}", "-" + format_chf(result.discount)))
    for vat in result.vat_lines:
        rows.append(total_row(f"VAT {vat.rate}% ({vat.category})", format_chf(vat.vat)))
    rows.append(total_row("Total", format_chf(result.total)))
    rows.append(total_row("Total (cash)", format_chf(result.cash_total)))
    return "\n".join(rows)


def to_json(result: Quote) -> dict[str, object]:
    return {
        "lines": [
            {
                "sku": line.sku,
                "quantity": line.quantity,
                "net": str(line.net),
                "discount": str(line.discount),
                "vat_category": line.vat_category.value,
            }
            for line in result.lines
        ],
        "subtotal": str(result.subtotal),
        "coupon": result.coupon_code,
        "discount": str(result.discount),
        "vat": [
            {"category": v.category.value, "rate": str(v.rate), "vat": str(v.vat)}
            for v in result.vat_lines
        ],
        "total": str(result.total),
        "cash_total": str(result.cash_total),
    }


def _run_quote(args: argparse.Namespace) -> str:
    cart_file = load_cart(args.cart)
    code: str | None = args.coupon or cart_file.coupon_code
    coupon: Coupon | None = None
    if code is not None:
        book = load_coupons(args.coupons) if args.coupons else CouponBook()
        coupon = book.find(code)
    result = quote(cart_file.cart, today=args.today or date.today(), coupon=coupon)
    if args.json:
        return json.dumps(to_json(result), indent=2)
    return render(result)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        output = _run_quote(args)
    except ShopkitError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR
    print(output)
    return EXIT_OK
