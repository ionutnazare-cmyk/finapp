from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from finapp.infrastructure.dividends.csv_provider import CsvDividendProvider

CSV_CONTENT = """symbol,amount_per_share,currency,pay_date
TLV,0.22,RON,2025-06-15
TLV,0.25,RON,2026-06-14
SNP,0.04,RON,2025-08-20
"""

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "bvb_dividends_sample.csv"


@pytest.fixture
def csv_path(tmp_path: Path) -> Path:
    path = tmp_path / "dividends.csv"
    path.write_text(CSV_CONTENT, encoding="utf-8")
    return path


def test_loads_and_groups_by_symbol_sorted_by_date(csv_path: Path) -> None:
    provider = CsvDividendProvider(csv_path)
    dividends = provider.get_dividends("tlv")
    assert [str(d.amount_per_share.amount) for d in dividends] == ["0.22", "0.25"]


def test_get_latest_dividend(csv_path: Path) -> None:
    provider = CsvDividendProvider(csv_path)
    latest = provider.get_latest_dividend("TLV")
    assert latest is not None
    assert latest.amount_per_share.amount == Decimal("0.25")


def test_missing_symbol_returns_empty(csv_path: Path) -> None:
    provider = CsvDividendProvider(csv_path)
    assert provider.get_dividends("UNKNOWN") == ()


def test_missing_required_column_raises(tmp_path: Path) -> None:
    bad_path = tmp_path / "bad.csv"
    bad_path.write_text("symbol,amount_per_share\nTLV,0.25\n", encoding="utf-8")
    with pytest.raises(ValueError):
        CsvDividendProvider(bad_path)


def test_refresh_reloads_from_disk(csv_path: Path) -> None:
    provider = CsvDividendProvider(csv_path)
    csv_path.write_text(
        "symbol,amount_per_share,currency,pay_date\nTLV,0.30,RON,2027-06-14\n", encoding="utf-8"
    )
    provider.refresh()
    latest = provider.get_latest_dividend("TLV")
    assert latest is not None
    assert latest.amount_per_share.amount == Decimal("0.30")


def test_loads_sample_fixture() -> None:
    provider = CsvDividendProvider(FIXTURE_PATH)
    latest_tlv = provider.get_latest_dividend("TLV")
    assert latest_tlv is not None
    assert latest_tlv.amount_per_share.amount == Decimal("0.2500")
