from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from shopkit import __version__
from shopkit.cli import _row, main

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


def test_the_text_quote_layout_is_pinned(capsys: pytest.CaptureFixture[str]) -> None:
    # Complete text output for a coupon and two VAT rates; changing the layout must show up here.
    assert main(["quote", CART, "--coupons", COUPONS, "--today", "2026-10-01"]) == 0
    assert capsys.readouterr().out == (
        "  3 x Green tea, 100 g         CHF 14.70\n"
        "  2 x Stoneware mug            CHF 36.00\n"
        "  1 x The Art of Brewing       CHF 29.00\n"
        "Subtotal                       CHF 79.70\n"
        "Items: 6\n"
        "Coupon WELCOME10               -CHF 7.97\n"
        "VAT 8.1% (standard)             CHF 2.62\n"
        "VAT 2.6% (reduced)              CHF 1.02\n"
        "Total                          CHF 75.37\n"
        "Total (cash)                   CHF 75.35\n"
    )


def test_a_row_right_aligns_the_amount_at_the_existing_width() -> None:
    # Label padded to 10, two spaces, amount right-aligned in 14 columns.
    assert _row("Total", "CHF 1.00", 10) == "Total" + " " * 13 + "CHF 1.00"
    assert len(_row("Total", "CHF 1.00", 10)) == 10 + 2 + 14


def test_a_row_does_not_clip_a_label_or_amount_wider_than_its_column() -> None:
    # Amount of 16 characters is wider than the 14-column amount field: written in full.
    assert _row("A", "CHF 1'000'000.00", 3) == "A" + " " * 4 + "CHF 1'000'000.00"
    # Label longer than the label column is written in full, amount still right-aligned.
    assert _row("Coupon WELCOME10", "-CHF 7.97", 5) == "Coupon WELCOME10" + " " * 7 + "-CHF 7.97"


def test_the_text_quote_shows_the_item_count_after_the_subtotal(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["quote", CART, "--coupons", COUPONS, "--today", "2026-10-01"]) == 0
    lines = capsys.readouterr().out.splitlines()
    subtotal = next(i for i, line in enumerate(lines) if line.startswith("Subtotal"))
    # 3 x tea + 2 x mug + 1 x book
    assert lines[subtotal + 1] == "Items: 6"


def test_the_json_quote_has_the_same_keys_and_no_item_count(
    capsys: pytest.CaptureFixture[str],
) -> None:
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
    assert set(result["lines"][0]) == {
        "sku",
        "quantity",
        "net",
        "discount",
        "vat_category",
    }
    assert [line["quantity"] for line in result["lines"]] == [3, 2, 1]


def test_json_quote(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["quote", CART, "--coupons", COUPONS, "--today", "2026-10-01", "--json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["coupon"] == "WELCOME10"
    assert result["discount"] == "7.97"
    assert result["total"] == "75.37"
    assert result["cash_total"] == "75.35"


def test_an_empty_cart_quotes_zero(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    cart_file = tmp_path / "empty.json"
    cart_file.write_text(json.dumps({"lines": []}), encoding="utf-8")
    assert main(["quote", str(cart_file)]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert [" ".join(line.split()) for line in lines] == [
        "Subtotal CHF 0.00",
        "Items: 0",
        "Total CHF 0.00",
        "Total (cash) CHF 0.00",
    ]


def test_a_lower_case_coupon_code_is_accepted(capsys: pytest.CaptureFixture[str]) -> None:
    args = ["quote", CART, "--coupons", COUPONS, "--coupon", "welcome10", "--today", "2026-10-01"]
    assert main([*args, "--json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["coupon"] == "WELCOME10"
    assert result["discount"] == "7.97"


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


def test_coupons_lists_one_line_per_coupon_in_file_order(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["coupons", COUPONS]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "WELCOME10  10%  2030-12-31  min CHF 20.00",
        "FIVEOFF  CHF 5.00  no end date  min CHF 30.00",
        "SPRING15  15%  2026-05-31",
    ]


def test_coupons_lists_a_two_coupon_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    coupon_file = tmp_path / "two.json"
    coupon_file.write_text(
        json.dumps(
            [
                {"code": "ZETA", "kind": "fixed", "value": "2.50"},
                {"code": "ALPHA", "kind": "percent", "value": "20", "valid_until": "2027-01-01"},
            ]
        ),
        encoding="utf-8",
    )
    assert main(["coupons", str(coupon_file)]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "ZETA  CHF 2.50  no end date",
        "ALPHA  20%  2027-01-01",
    ]


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ('{"code": "NOPE"}', "coupons: expected a list"),
        ('[{"code": "X1", "kind": "bogus", "value": "1"}]', "coupons[0]"),
        ("[", "invalid JSON"),
    ],
)
def test_coupons_with_an_invalid_file_exits_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], content: str, message: str
) -> None:
    coupon_file = tmp_path / "bad.json"
    coupon_file.write_text(content, encoding="utf-8")
    assert main(["coupons", str(coupon_file)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert message in captured.err


def test_coupons_with_a_missing_file_exits_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["coupons", str(tmp_path / "nope.json")]) == 2
    assert "file not found" in capsys.readouterr().err
