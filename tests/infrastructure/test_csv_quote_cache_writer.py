from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd

from finapp.application.dto import Quote
from finapp.domain.value_objects.enums import Currency
from finapp.domain.value_objects.money import Money
from finapp.infrastructure.market_data.csv_quote_cache_writer import CsvQuoteCacheWriter


def _quote(symbol: str, amount: str) -> Quote:
    return Quote(
        symbol=symbol,
        price=Money(amount=Decimal(amount), currency=Currency.RON),
        as_of=date(2026, 8, 28),
    )


def test_creates_file_if_missing(tmp_path: Path) -> None:
    path = tmp_path / "quotes.csv"
    CsvQuoteCacheWriter(path).save_quotes([_quote("TLV", "5.00")])

    assert path.exists()
    frame = pd.read_csv(path)
    assert list(frame.columns) == ["symbol", "price", "currency", "as_of"]
    assert frame.iloc[0]["symbol"] == "TLV"


def test_updates_existing_symbol_preserving_others(tmp_path: Path) -> None:
    path = tmp_path / "quotes.csv"
    path.write_text(
        "symbol,price,currency,as_of\nTLV,4.00,RON,2026-08-01\nSNP,0.50,RON,2026-08-01\n"
    )

    CsvQuoteCacheWriter(path).save_quotes([_quote("TLV", "5.00")])

    frame = pd.read_csv(path)
    tlv_row = frame[frame["symbol"] == "TLV"].iloc[0]
    assert float(tlv_row["price"]) == 5.00
    snp_row = frame[frame["symbol"] == "SNP"].iloc[0]
    assert float(snp_row["price"]) == 0.50
    assert len(frame) == 2


def test_appends_new_symbol(tmp_path: Path) -> None:
    path = tmp_path / "quotes.csv"
    path.write_text("symbol,price,currency,as_of\nTLV,4.00,RON,2026-08-01\n")

    CsvQuoteCacheWriter(path).save_quotes([_quote("SNP", "0.55")])

    frame = pd.read_csv(path)
    assert len(frame) == 2
    assert set(frame["symbol"]) == {"TLV", "SNP"}


def test_empty_quotes_does_nothing(tmp_path: Path) -> None:
    path = tmp_path / "quotes.csv"
    CsvQuoteCacheWriter(path).save_quotes([])
    assert not path.exists()


def test_creates_parent_directories(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "dir" / "quotes.csv"
    CsvQuoteCacheWriter(path).save_quotes([_quote("TLV", "5.00")])
    assert path.exists()
