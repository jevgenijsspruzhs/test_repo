from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from shopkit import __version__
from shopkit.cli import _format_row, main

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
CART = str(EXAMPLES / "cart.json")
COUPONS = str(EXAMPLES / "coupons.json")

GOLDEN_TEXT = """\
  3 x Green tea, 100 g         CHF 14.70
  2 x Stoneware mug            CHF 36.00
  1 x The Art of Brewing       CHF 29.00
Subtotal                       CHF 79.70
Coupon WELCOME10               -CHF 7.97
VAT 8.1% (standard)             CHF 2.62
VAT 2.6% (reduced)              CHF 1.02
Total                          CHF 75.37
Total (cash)                   CHF 75.35
"""


def test_text_quote(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["quote", CART, "--coupons", COUPONS, "--today", "2026-10-01"]) == 0
    output = capsys.readouterr().out
    assert "Green tea, 100 g" in output
    assert "Coupon WELCOME10" in output
    assert "VAT 8.1% (standard)" in output
    assert output.splitlines()[-1].endswith("CHF 75.35")


def test_text_quote_golden_output(capsys: pytest.CaptureFixture[str]) -> None:
    # Captured from the text renderer before _format_row was introduced. Any change to the
    # plain-text layout (columns, padding, labels) must be deliberate and update this text.
    assert main(["quote", CART, "--coupons", COUPONS, "--today", "2026-10-01"]) == 0
    assert capsys.readouterr().out == GOLDEN_TEXT


def test_format_row_pads_label_and_right_aligns_amount() -> None:
    # Label is left-aligned in the label column, then two spaces, then a 14-column amount.
    assert _format_row("Tea", "CHF 1.00", 6) == "Tea" + " " * 11 + "CHF 1.00"
    assert _format_row("Tea", "CHF 1'234.50", 6) == "Tea" + " " * 7 + "CHF 1'234.50"


def test_format_row_keeps_long_labels_and_amounts_whole() -> None:
    # A label wider than the column is not truncated; the amount column still follows it.
    assert _format_row("Very long label", "CHF 1.00", 4) == "Very long label" + " " * 8 + "CHF 1.00"
    # An amount wider than 14 columns is not truncated either.
    assert _format_row("x", "CHF 1'234'567.89", 3) == "x" + " " * 4 + "CHF 1'234'567.89"


def test_format_row_output_has_fixed_width_for_fitting_labels() -> None:
    rows = [_format_row(label, "CHF 0.05", 12) for label in ("a", "Subtotal", "x" * 12)]
    assert {len(row) for row in rows} == {12 + 2 + 14}


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
