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


# The complete text output for a cart with a coupon and two VAT rates (standard and reduced).
# Pins the column layout: a change to any row's width or alignment must show up here.
GOLDEN_TEXT_QUOTE = (
    "  3 x Green tea, 100 g         CHF 14.70\n"
    "  2 x Stoneware mug            CHF 36.00\n"
    "  1 x The Art of Brewing       CHF 29.00\n"
    "Subtotal                       CHF 79.70\n"
    "Coupon WELCOME10               -CHF 7.97\n"
    "VAT 8.1% (standard)             CHF 2.62\n"
    "VAT 2.6% (reduced)              CHF 1.02\n"
    "Total                          CHF 75.37\n"
    "Total (cash)                   CHF 75.35\n"
)


def test_text_quote_golden_output(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["quote", CART, "--coupons", COUPONS, "--today", "2026-10-01"]) == 0
    assert capsys.readouterr().out == GOLDEN_TEXT_QUOTE


def test_json_quote(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["quote", CART, "--coupons", COUPONS, "--today", "2026-10-01", "--json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["coupon"] == "WELCOME10"
    assert result["discount"] == "7.97"
    assert result["total"] == "75.37"
    assert result["cash_total"] == "75.35"


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
