"""Reading carts and coupons from JSON files.

A cart file::

    {
      "lines": [
        {"sku": "TEA-GREEN", "name": "Green tea", "unit_price": "4.90",
         "quantity": 3, "vat": "reduced"}
      ],
      "coupon": "WELCOME10"
    }

``unit_price`` is a string (never a JSON number, which would be a float); ``vat`` defaults to
``standard``; ``coupon`` is optional.

A coupon file is a list of coupons::

    [{"code": "WELCOME10", "kind": "percent", "value": "10",
      "valid_until": "2030-12-31", "min_subtotal": "20.00"}]
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, cast

from shopkit.cart import Cart
from shopkit.catalog import Product
from shopkit.coupons import Coupon, CouponBook, CouponKind
from shopkit.errors import CartFileError, ShopkitError
from shopkit.money import ZERO, parse_amount
from shopkit.vat import VatCategory, parse_category


@dataclass(frozen=True, slots=True)
class CartFile:
    cart: Cart
    coupon_code: str | None


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise CartFileError(f"{path}: file not found") from None
    except (OSError, UnicodeDecodeError) as exc:
        raise CartFileError(f"{path}: cannot read file ({exc.__class__.__name__})") from None
    except json.JSONDecodeError as exc:
        raise CartFileError(f"{path}: invalid JSON (line {exc.lineno})") from None


def _field(item: dict[str, Any], key: str, where: str, kind: type, *, required: bool = True) -> Any:
    if key not in item:
        if required:
            raise CartFileError(f"{where}.{key}: missing")
        return None
    value = item[key]
    if not isinstance(value, kind) or isinstance(value, bool):
        raise CartFileError(f"{where}.{key}: expected {kind.__name__}")
    return value


def parse_cart(data: object) -> CartFile:
    if not isinstance(data, dict):
        raise CartFileError("cart: expected an object")
    document = cast(dict[str, Any], data)
    lines = document.get("lines", [])
    if not isinstance(lines, list):
        raise CartFileError("cart.lines: expected a list")
    cart = Cart()
    for index, raw in enumerate(cast(list[object], lines)):
        where = f"lines[{index}]"
        if not isinstance(raw, dict):
            raise CartFileError(f"{where}: expected an object")
        item = cast(dict[str, Any], raw)
        try:
            vat = _field(item, "vat", where, str, required=False)
            product = Product(
                sku=_field(item, "sku", where, str),
                name=_field(item, "name", where, str),
                unit_price=parse_amount(_field(item, "unit_price", where, str)),
                vat_category=VatCategory.STANDARD if vat is None else parse_category(vat),
            )
            cart.add(product, _field(item, "quantity", where, int))
        except CartFileError:
            raise
        except (ShopkitError, ValueError, TypeError) as exc:
            raise CartFileError(f"{where}: {exc}") from None
    coupon = _field(document, "coupon", "cart", str, required=False)
    return CartFile(cart, coupon or None)


def parse_coupons(data: object) -> CouponBook:
    if not isinstance(data, list):
        raise CartFileError("coupons: expected a list")
    coupons: list[Coupon] = []
    for index, raw in enumerate(cast(list[object], data)):
        where = f"coupons[{index}]"
        if not isinstance(raw, dict):
            raise CartFileError(f"{where}: expected an object")
        item = cast(dict[str, Any], raw)
        try:
            valid_until = _field(item, "valid_until", where, str, required=False)
            min_subtotal = _field(item, "min_subtotal", where, str, required=False)
            coupons.append(
                Coupon(
                    code=_field(item, "code", where, str),
                    kind=CouponKind(_field(item, "kind", where, str)),
                    value=parse_amount(_field(item, "value", where, str)),
                    valid_until=None if valid_until is None else date.fromisoformat(valid_until),
                    min_subtotal=ZERO if min_subtotal is None else parse_amount(min_subtotal),
                )
            )
        except CartFileError:
            raise
        except (ShopkitError, ValueError) as exc:
            raise CartFileError(f"{where}: {exc}") from None
    try:
        return CouponBook(coupons)
    except ValueError as exc:
        raise CartFileError(f"coupons: {exc}") from None


def load_cart(path: Path) -> CartFile:
    return parse_cart(_read_json(path))


def load_coupons(path: Path) -> CouponBook:
    return parse_coupons(_read_json(path))
