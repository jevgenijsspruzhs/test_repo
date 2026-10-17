from __future__ import annotations

import json
from pathlib import Path

import pytest

from shopkit.cli import main

TWO_COUPONS = [
    {
        "code": "WELCOME10",
        "kind": "percent",
        "value": "10",
        "valid_until": "2030-12-31",
        "min_subtotal": "20.00",
    },
    {"code": "FIVEOFF", "kind": "fixed", "value": "5.00"},
]


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_lists_each_coupon_in_file_order(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    coupon_file = _write(tmp_path / "coupons.json", json.dumps(TWO_COUPONS))
    assert main(["coupons", str(coupon_file)]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 2
    first, second = (" ".join(line.split()) for line in lines)
    assert first == "WELCOME10 10% 2030-12-31 min CHF 20.00"
    assert second == "FIVEOFF CHF 5.00 no end date"


def test_lists_the_example_file(capsys: pytest.CaptureFixture[str]) -> None:
    example = Path(__file__).resolve().parent.parent / "examples" / "coupons.json"
    assert main(["coupons", str(example)]) == 0
    codes = [line.split()[0] for line in capsys.readouterr().out.splitlines()]
    assert codes == ["WELCOME10", "FIVEOFF", "SPRING15"]


def test_an_empty_coupon_file_prints_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    coupon_file = _write(tmp_path / "coupons.json", "[]")
    assert main(["coupons", str(coupon_file)]) == 0
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("[{", "invalid JSON"),
        ('{"code": "WELCOME10"}', "coupons: expected a list"),
        ('[{"code": "WELCOME10", "kind": "percent"}]', "coupons[0].value: missing"),
        ('[{"code": "bad code", "kind": "fixed", "value": "5.00"}]', "coupons[0]"),
        ('[{"code": "A1", "kind": "fixed", "value": "5.00"}] x', "invalid JSON"),
    ],
)
def test_an_invalid_coupon_file_exits_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], text: str, message: str
) -> None:
    coupon_file = _write(tmp_path / "coupons.json", text)
    assert main(["coupons", str(coupon_file)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert message in captured.err


def test_a_duplicate_code_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    coupon_file = _write(tmp_path / "coupons.json", json.dumps(TWO_COUPONS + TWO_COUPONS[1:]))
    assert main(["coupons", str(coupon_file)]) == 2
    assert "duplicate coupon code: FIVEOFF" in capsys.readouterr().err


def test_a_missing_file_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["coupons", str(tmp_path / "nope.json")]) == 2
    assert "file not found" in capsys.readouterr().err


def test_a_coupon_file_is_required(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["coupons"])
    assert excinfo.value.code == 2
    assert "file" in capsys.readouterr().err
