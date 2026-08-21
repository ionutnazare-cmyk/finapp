"""Sprint 1.1 smoke tests.

These tests exist to prove the project skeleton is installable, importable,
and that the CLI entry point runs. Feature-level tests are added alongside
each future sprint's domain/application logic.
"""

from __future__ import annotations

import re

import pytest

import finapp
from finapp.presentation.cli import build_parser, main


def test_package_exposes_version() -> None:
    assert re.match(r"^\d+\.\d+\.\d+$", finapp.__version__)


def test_cli_parser_has_version_flag() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["--version"])
    assert exc_info.value.code == 0


def test_cli_main_returns_zero(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main([])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "FinApp" in captured.out
