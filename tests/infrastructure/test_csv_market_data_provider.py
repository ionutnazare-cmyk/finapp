from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from finapp.application.exceptions import QuoteNotFoundError
from finapp.infrastructure.market_data.csv_provider import CsvMarketDataProvider

CSV_CONTENT = """symbol,price,currency,as_of
TLV,4.50,RON,2026-08-21
SNP,0.55,RON,2026-08-21
H2O,105.20,RON,2026-08-20
"""

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "bvb_quotes_sample.csv"


@pytest.fixture
def csv_path(tmp_path: Path) -> Path:
    path = tmp_path / "quotes.csv"
    path.write_text(CSV_CONTENT, encoding="utf-8")
    return path


def test_loads_quotes_from_csv(csv_path: Path) -> None:
    provider = CsvMarketDataProvider(csv_path)
    quote = provider.get_quote("tlv")
    assert quote.price.amount == Decimal("4.50")
    assert quote.as_of.isoformat() == "2026-08-21"


def test_missing_symbol_raises(csv_path: Path) -> None:
    provider = CsvMarketDataProvider(csv_path)
    with pytest.raises(QuoteNotFoundError):
        provider.get_quote("UNKNOWN")


def test_missing_required_column_raises(tmp_path: Path) -> None:
    bad_path = tmp_path / "bad.csv"
    bad_path.write_text("symbol,price\nTLV,4.5\n", encoding="utf-8")
    with pytest.raises(ValueError):
        CsvMarketDataProvider(bad_path)


def test_invalid_price_raises(tmp_path: Path) -> None:
    bad_path = tmp_path / "bad_price.csv"
    bad_path.write_text(
        "symbol,price,currency,as_of\nTLV,not-a-number,RON,2026-08-21\n", encoding="utf-8"
    )
    with pytest.raises(ValueError):
        CsvMarketDataProvider(bad_path)


def test_refresh_reloads_from_disk(csv_path: Path) -> None:
    provider = CsvMarketDataProvider(csv_path)
    csv_path.write_text(
        "symbol,price,currency,as_of\nTLV,5.00,RON,2026-08-22\n", encoding="utf-8"
    )
    provider.refresh()
    quote = provider.get_quote("TLV")
    assert quote.price.amount == Decimal("5.00")


def test_loads_sample_fixture() -> None:
    provider = CsvMarketDataProvider(FIXTURE_PATH)
    quotes = provider.get_quotes(["TLV", "SNP", "H2O", "SNG", "EL", "FP"])
    assert quotes["TLV"].price.amount == Decimal("4.5020")
    assert len(quotes) == 6
