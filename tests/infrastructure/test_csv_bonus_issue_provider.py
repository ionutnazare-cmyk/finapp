from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from finapp.infrastructure.bonus_issues.csv_provider import CsvBonusIssueProvider

CSV_CONTENT = """symbol,new_shares_per_held_share,record_date
TLV,0.17,2025-04-10
TLV,0.19,2026-04-09
"""

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "bvb_bonus_issues_sample.csv"


@pytest.fixture
def csv_path(tmp_path: Path) -> Path:
    path = tmp_path / "bonus_issues.csv"
    path.write_text(CSV_CONTENT, encoding="utf-8")
    return path


def test_loads_and_groups_by_symbol_sorted_by_date(csv_path: Path) -> None:
    provider = CsvBonusIssueProvider(csv_path)
    issues = provider.get_bonus_issues("tlv")
    assert [str(i.new_shares_per_held_share) for i in issues] == ["0.17", "0.19"]


def test_get_latest_bonus_issue(csv_path: Path) -> None:
    provider = CsvBonusIssueProvider(csv_path)
    latest = provider.get_latest_bonus_issue("TLV")
    assert latest is not None
    assert latest.new_shares_per_held_share == Decimal("0.19")


def test_missing_symbol_returns_empty(csv_path: Path) -> None:
    provider = CsvBonusIssueProvider(csv_path)
    assert provider.get_bonus_issues("UNKNOWN") == ()


def test_missing_required_column_raises(tmp_path: Path) -> None:
    bad_path = tmp_path / "bad.csv"
    bad_path.write_text("symbol,new_shares_per_held_share\nTLV,0.25\n", encoding="utf-8")
    with pytest.raises(ValueError):
        CsvBonusIssueProvider(bad_path)


def test_refresh_reloads_from_disk(csv_path: Path) -> None:
    provider = CsvBonusIssueProvider(csv_path)
    csv_path.write_text(
        "symbol,new_shares_per_held_share,record_date\nTLV,0.20,2027-04-08\n", encoding="utf-8"
    )
    provider.refresh()
    latest = provider.get_latest_bonus_issue("TLV")
    assert latest is not None
    assert latest.new_shares_per_held_share == Decimal("0.20")


def test_loads_sample_fixture() -> None:
    provider = CsvBonusIssueProvider(FIXTURE_PATH)
    latest = provider.get_latest_bonus_issue("TLV")
    assert latest is not None
    assert latest.new_shares_per_held_share == Decimal("0.1900")
