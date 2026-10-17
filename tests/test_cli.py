from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from shopkit import __version__
from shopkit.cli import main

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
CART = str(EXAMPLES / "cart.json")
COUPONS = str(EXAMPLES / "coupons.json")


def test_text_quote(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["quote", CART, "--coupons", COUPONS, "--today", "2026-10-01"]) == 0
    output = capsys.readouterr().out
    assert "Green tea, 100 g" in output
    assert "Coupon WELCOME10" in output
    assert "VAT 8.1% (standard)" in output
    assert output.splitlines()[-1].endswith("CHF 75.35")


def test_text_quote_shows_the_item_count_after_the_subtotal(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # The example cart has 3 x tea, 2 x mug and 1 x book: 6 items in total.
    assert main(["quote", CART, "--coupons", COUPONS, "--today", "2026-10-01"]) == 0
    lines = capsys.readouterr().out.splitlines()
    subtotal = next(i for i, line in enumerate(lines) if line.startswith("Subtotal"))
    assert lines[subtotal + 1] == "Items: 6"
    assert sum(line.startswith("Items: ") for line in lines) == 1


def test_text_quote_item_count_sums_all_quantities(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cart_file = tmp_path / "cart.json"
    cart_file.write_text(
        json.dumps(
            {
                "lines": [
                    {"sku": "ALPHA-01", "name": "Alpha", "unit_price": "1.00", "quantity": 7},
                    {"sku": "BETA-01", "name": "Beta", "unit_price": "2.50", "quantity": 1},
                    {"sku": "GAMMA-01", "name": "Gamma", "unit_price": "3.00", "quantity": 12},
                    {"sku": "DELTA-01", "name": "Delta", "unit_price": "4.00", "quantity": 2},
                ]
            }
        ),
        encoding="utf-8",
    )
    assert main(["quote", str(cart_file), "--today", "2026-10-01"]) == 0
    lines = capsys.readouterr().out.splitlines()
    subtotal = next(i for i, line in enumerate(lines) if line.startswith("Subtotal"))
    assert lines[subtotal + 1] == "Items: 22"


def test_json_quote(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["quote", CART, "--coupons", COUPONS, "--today", "2026-10-01", "--json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["coupon"] == "WELCOME10"
    assert result["discount"] == "7.97"
    assert result["total"] == "75.37"
    assert result["cash_total"] == "75.35"


def test_json_quote_keys_are_unchanged(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["quote", CART, "--coupons", COUPONS, "--today", "2026-10-01", "--json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert set(result) == {
        "lines",
        "subtotal",
        "coupon",
        "discount",
        "vat",
        "total",
        "cash_total",
    }
    assert [line["quantity"] for line in result["lines"]] == [3, 2, 1]
    assert result["subtotal"] == "79.70"


def test_the_coupon_option_overrides_the_cart(capsys: pytest.CaptureFixture[str]) -> None:
    args = ["quote", CART, "--coupons", COUPONS, "--coupon", "FIVEOFF", "--today", "2026-10-01"]
    assert main([*args, "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["discount"] == "5.00"


@pytest.mark.parametrize(
    ("extra", "message"),
    [
        ([], "does not exist"),  # no coupon file: every code is unknown
        (["--coupons", COUPONS, "--coupon", "NOPE"], "does not exist"),
        (["--coupons", COUPONS, "--coupon", "SPRING15"], "expired"),
    ],
)
def test_coupon_errors_exit_2(
    capsys: pytest.CaptureFixture[str], extra: list[str], message: str
) -> None:
    assert main(["quote", CART, "--today", "2026-10-01", *extra]) == 2
    assert message in capsys.readouterr().err


def test_a_missing_cart_file_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["quote", str(tmp_path / "nope.json")]) == 2
    assert "file not found" in capsys.readouterr().err


def test_an_invalid_date_is_a_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["quote", CART, "--today", "01.10.2026"])
    assert excinfo.value.code == 2
    assert "not a date" in capsys.readouterr().err


def test_module_entry_point() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "shopkit", "--version"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert completed.stdout.strip() == f"shopkit {__version__}"
