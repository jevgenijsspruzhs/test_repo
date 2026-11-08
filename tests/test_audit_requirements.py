from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_audit_requirements_file_lists_exactly_the_fixture_package() -> None:
    lines = (REPO_ROOT / "requirements-audit.txt").read_text(encoding="utf-8").splitlines()
    assert lines == ["polis-fixture-pkg==1.0.0"]
