from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd

from finapp.domain.value_objects.dividend import Dividend
from finapp.domain.value_objects.enums import Currency
from finapp.domain.value_objects.money import Money
from finapp.infrastructure.dividends.csv_dividend_cache_writer import (
    CsvDividendCacheWriter,
)


def _dividend(symbol: str, amount: str, year: int) -> Dividend:
    return Dividend(
        symbol=symbol,
        amount_per_share=Money(amount=Decimal(amount), currency=Currency.RON),
        pay_date=date(year, 12, 31),
    )


def test_creates_file_if_missing(tmp_path: Path) -> None:
    path = tmp_path / "dividends.csv"
    CsvDividendCacheWriter(path).save_dividends([_dividend("TLV", "0.25", 2026)])

    assert path.exists()
    frame = pd.read_csv(path)
    assert list(frame.columns) == ["symbol", "amount_per_share", "currency", "pay_date"]
    assert frame.iloc[0]["symbol"] == "TLV"


def test_replaces_existing_entry_for_same_symbol_and_year(tmp_path: Path) -> None:
    path = tmp_path / "dividends.csv"
    path.write_text(
        "symbol,amount_per_share,currency,pay_date\nTLV,0.20,RON,2026-06-14\n"
    )

    # A BVB-fetched entry for the same year (but a different, synthetic
    # Dec 31 date) should replace the existing row, not duplicate it.
    CsvDividendCacheWriter(path).save_dividends([_dividend("TLV", "0.25", 2026)])

    frame = pd.read_csv(path)
    assert len(frame) == 1
    assert float(frame.iloc[0]["amount_per_share"]) == 0.25


def test_keeps_entries_for_other_years(tmp_path: Path) -> None:
    path = tmp_path / "dividends.csv"
    path.write_text(
        "symbol,amount_per_share,currency,pay_date\nTLV,0.20,RON,2025-06-14\n"
    )

    CsvDividendCacheWriter(path).save_dividends([_dividend("TLV", "0.25", 2026)])

    frame = pd.read_csv(path)
    assert len(frame) == 2
    assert set(frame["pay_date"]) == {"2025-06-14", "2026-12-31"}


def test_keeps_entries_for_other_symbols(tmp_path: Path) -> None:
    path = tmp_path / "dividends.csv"
    path.write_text(
        "symbol,amount_per_share,currency,pay_date\nSNP,0.04,RON,2026-08-20\n"
    )

    CsvDividendCacheWriter(path).save_dividends([_dividend("TLV", "0.25", 2026)])

    frame = pd.read_csv(path)
    assert len(frame) == 2
    assert set(frame["symbol"]) == {"TLV", "SNP"}


def test_empty_dividends_does_nothing(tmp_path: Path) -> None:
    path = tmp_path / "dividends.csv"
    CsvDividendCacheWriter(path).save_dividends([])
    assert not path.exists()


def test_creates_parent_directories(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "dir" / "dividends.csv"
    CsvDividendCacheWriter(path).save_dividends([_dividend("TLV", "0.25", 2026)])
    assert path.exists()
