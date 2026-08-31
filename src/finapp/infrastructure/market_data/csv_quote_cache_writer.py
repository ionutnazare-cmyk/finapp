"""Writes freshly-fetched quotes into the local CSV cache that
:class:`~finapp.infrastructure.market_data.csv_provider.CsvMarketDataProvider`
reads from — merging with whatever's already there rather than overwriting
the whole file, so refreshing a few symbols doesn't wipe out data for
symbols not included in this batch.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pandas as pd

from finapp.application.dto import Quote
from finapp.application.ports import QuoteCacheWriter

_COLUMNS = ("symbol", "price", "currency", "as_of")


class CsvQuoteCacheWriter(QuoteCacheWriter):
    """Merges the given quotes into ``csv_path``, keyed by symbol: an
    existing row for a symbol is replaced, a new symbol is appended, and
    rows for symbols not in this batch are left untouched.
    """

    def __init__(self, csv_path: Path) -> None:
        self._csv_path = csv_path

    def save_quotes(self, quotes: Iterable[Quote]) -> None:
        quotes_by_symbol = {quote.symbol: quote for quote in quotes}
        if not quotes_by_symbol:
            return

        rows: dict[str, dict[str, str]] = {}
        if self._csv_path.exists():
            frame = pd.read_csv(self._csv_path, dtype=str)
            for _, row in frame.iterrows():
                symbol = str(row["symbol"]).strip().upper()
                rows[symbol] = {
                    "symbol": symbol,
                    "price": str(row["price"]),
                    "currency": str(row["currency"]),
                    "as_of": str(row["as_of"]),
                }

        for symbol, quote in quotes_by_symbol.items():
            rows[symbol] = {
                "symbol": symbol,
                "price": str(quote.price.amount),
                "currency": quote.price.currency.value,
                "as_of": quote.as_of.isoformat(),
            }

        self._csv_path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(list(rows.values()), columns=list(_COLUMNS)).to_csv(
            self._csv_path, index=False
        )
