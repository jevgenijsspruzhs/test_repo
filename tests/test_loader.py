from __future__ import annotations

import json
import re
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from shopkit.coupons import CouponKind
from shopkit.errors import CartFileError
from shopkit.loader import load_cart, load_coupons, parse_cart, parse_coupons
from shopkit.vat import VatCategory

LINE = {
    "sku": "TEA-GREEN",
    "name": "Green tea",
    "unit_price": "4.90",
    "quantity": 3,
    "vat": "reduced",
}


def test_parse_a_cart() -> None:
    standard = {key: value for key, value in LINE.items() if key != "vat"} | {"sku": "TEA-BLACK"}
    parsed = parse_cart({"lines": [LINE, standard], "coupon": "WELCOME10"})
    first, second = parsed.cart.lines
    assert (first.product.unit_price, first.quantity) == (Decimal("4.90"), 3)
    assert first.product.vat_category is VatCategory.REDUCED
    assert second.product.vat_category is VatCategory.STANDARD
    assert parsed.coupon_code == "WELCOME10"


def test_a_cart_without_coupon_or_lines() -> None:
    parsed = parse_cart({})
    assert parsed.cart.is_empty
    assert parsed.coupon_code is None


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"unit_price": 4.9}, r"lines\[0\]\.unit_price: expected str"),
        ({"quantity": "3"}, r"lines\[0\]\.quantity: expected int"),
        ({"quantity": True}, r"lines\[0\]\.quantity: expected int"),
        ({"vat": "luxury"}, r"lines\[0\]: unknown VAT category"),
        ({"unit_price": "4.999"}, r"lines\[0\]: amount has more than two decimal places"),
        ({"sku": "bad sku"}, r"lines\[0\]: invalid SKU"),
    ],
)
def test_invalid_lines(change: dict[str, Any], message: str) -> None:
    with pytest.raises(CartFileError, match=message):
        parse_cart({"lines": [{**LINE, **change}]})


def test_missing_field() -> None:
    line = {key: value for key, value in LINE.items() if key != "name"}
    with pytest.raises(CartFileError, match=r"lines\[0\]\.name: missing"):
        parse_cart({"lines": [line]})


@pytest.mark.parametrize("document", [[], {"lines": {}}, {"lines": ["x"]}, {"coupon": 10}])
def test_invalid_structure(document: object) -> None:
    with pytest.raises(CartFileError):
        parse_cart(document)


def test_parse_coupons() -> None:
    book = parse_coupons(
        [
            {
                "code": "WELCOME10",
                "kind": "percent",
                "value": "10",
                "valid_until": "2030-12-31",
                "min_subtotal": "20.00",
            },
            {"code": "FIVEOFF", "kind": "fixed", "value": "5.00"},
        ]
    )
    welcome = book.find("WELCOME10")
    assert welcome.kind is CouponKind.PERCENT
    assert welcome.valid_until == date(2030, 12, 31)
    assert book.find("FIVEOFF").min_subtotal == Decimal("0.00")


@pytest.mark.parametrize(
    "document",
    [
        {},
        [{"code": "X1", "kind": "percent", "value": "10"}],
        [{"code": "FIVEOFF", "kind": "gift", "value": "5.00"}],
        [{"code": "FIVEOFF", "kind": "fixed", "value": "5.00", "valid_until": "31.12.2030"}],
        [{"code": "FIVEOFF", "kind": "fixed", "value": "5.00"}] * 2,
    ],
)
def test_invalid_coupon_files(document: object) -> None:
    with pytest.raises(CartFileError):
        parse_coupons(document)


def test_load_files(tmp_path: Path) -> None:
    cart_path = tmp_path / "cart.json"
    cart_path.write_text(json.dumps({"lines": [LINE]}), encoding="utf-8")
    assert load_cart(cart_path).cart.subtotal == Decimal("14.70")
    coupons_path = tmp_path / "coupons.json"
    coupons_path.write_text("[]", encoding="utf-8")
    assert len(load_coupons(coupons_path)) == 0


def test_unreadable_files(tmp_path: Path) -> None:
    with pytest.raises(CartFileError, match="file not found"):
        load_cart(tmp_path / "missing.json")
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    with pytest.raises(CartFileError, match="invalid JSON"):
        load_cart(broken)


COUPON = {"code": "FIVEOFF", "kind": "fixed", "value": "5.00"}


def _write_coupons(tmp_path: Path, document: object) -> Path:
    path = tmp_path / "coupons.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


@pytest.mark.parametrize("document", [{"code": "FIVEOFF"}, "FIVEOFF", 5])
def test_coupon_file_must_be_a_list(tmp_path: Path, document: object) -> None:
    path = _write_coupons(tmp_path, document)
    with pytest.raises(CartFileError, match=r"coupons: expected a list"):
        load_coupons(path)


@pytest.mark.parametrize("entry", ["FIVEOFF", 5, ["FIVEOFF"], None])
def test_coupon_entry_must_be_an_object(tmp_path: Path, entry: object) -> None:
    path = _write_coupons(tmp_path, [COUPON, entry])
    with pytest.raises(CartFileError, match=r"coupons\[1\]: expected an object"):
        load_coupons(path)


def test_coupon_missing_code(tmp_path: Path) -> None:
    coupon = {key: value for key, value in COUPON.items() if key != "code"}
    path = _write_coupons(tmp_path, [COUPON, coupon])
    with pytest.raises(CartFileError, match=r"coupons\[1\]\.code: missing"):
        load_coupons(path)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"value": 5}, r"coupons\[1\]\.value: expected str"),
        ({"value": "ten"}, r"coupons\[1\]: not a valid amount"),
        ({"value": "0"}, r"coupons\[1\]: fixed discount must be positive"),
        ({"kind": "percent", "value": "150"}, r"coupons\[1\]: percentage must be in \(0, 100\]"),
    ],
)
def test_invalid_coupon_value(tmp_path: Path, change: dict[str, Any], message: str) -> None:
    path = _write_coupons(tmp_path, [COUPON, {**COUPON, **change}])
    with pytest.raises(CartFileError, match=message):
        load_coupons(path)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"valid_until": 20301231}, r"coupons\[1\]\.valid_until: expected str"),
        ({"valid_until": "31.12.2030"}, r"coupons\[1\]: "),
    ],
)
def test_invalid_coupon_date(tmp_path: Path, change: dict[str, Any], message: str) -> None:
    path = _write_coupons(tmp_path, [COUPON, {**COUPON, **change}])
    with pytest.raises(CartFileError, match=message):
        load_coupons(path)


def test_missing_coupon_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing-coupons.json"
    with pytest.raises(CartFileError, match=re.escape(f"{missing}: file not found")):
        load_coupons(missing)
