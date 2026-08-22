"""A :class:`MarketDataProvider` backed by a local CSV cache of quotes.

This adapter reads FinApp's own normalized quote schema, not BVB's raw
export format. A later sprint (automatic BVB data updates) will add a
scraper/client that fetches BVB's official data and writes it out in this
schema, refreshing the file this provider reads — that adapter will
implement the same :class:`~finapp.application.ports.MarketDataProvider`
port, so nothing above the infrastructure layer needs to change.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd

from finapp.application.dto import Quote
from finapp.application.exceptions import QuoteNotFoundError
from finapp.application.ports import MarketDataProvider
from finapp.domain.value_objects.enums import Currency
from finapp.domain.value_objects.money import Money

REQUIRED_COLUMNS = {"symbol", "price", "currency", "as_of"}


class CsvMarketDataProvider(MarketDataProvider):
    """Loads quotes from a CSV file with columns: ``symbol``, ``price``,
    ``currency``, ``as_of`` (ISO 8601 date, e.g. ``2026-08-21``).

    Quotes are loaded once at construction and cached in memory; call
    :meth:`refresh` to reload after the underlying file changes.
    """

    def __init__(self, csv_path: Path) -> None:
        self._csv_path = csv_path
        self._quotes: dict[str, Quote] = self._load()

    def _load(self) -> dict[str, Quote]:
        frame = pd.read_csv(self._csv_path, dtype={"symbol": str, "currency": str})

        missing_columns = REQUIRED_COLUMNS - set(frame.columns)
        if missing_columns:
            raise ValueError(
                f"CSV at {self._csv_path} is missing required columns: "
                f"{sorted(missing_columns)}"
            )

        quotes: dict[str, Quote] = {}
        for row in frame.itertuples(index=False):
            symbol = str(row.symbol).strip().upper()
            try:
                amount = Decimal(str(row.price))
            except InvalidOperation as exc:
                raise ValueError(
                    f"CSV at {self._csv_path}: invalid price for symbol '{symbol}': "
                    f"{row.price!r}"
                ) from exc

            quotes[symbol] = Quote(
                symbol=symbol,
                price=Money(amount=amount, currency=Currency(str(row.currency).strip().upper())),
                as_of=date.fromisoformat(str(row.as_of).strip()),
            )
        return quotes

    def get_quote(self, symbol: str) -> Quote:
        normalized = symbol.strip().upper()
        try:
            return self._quotes[normalized]
        except KeyError:
            raise QuoteNotFoundError(normalized) from None

    def get_quotes(self, symbols: Iterable[str]) -> Mapping[str, Quote]:
        return {symbol.strip().upper(): self.get_quote(symbol) for symbol in symbols}

    def refresh(self) -> None:
        """Reload quotes from disk, e.g. after the CSV cache has been updated."""

        self._quotes = self._load()
