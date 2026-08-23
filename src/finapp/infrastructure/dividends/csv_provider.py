"""A :class:`DividendProvider` backed by a local CSV cache of dividend payments.

Like :class:`~finapp.infrastructure.market_data.csv_provider.CsvMarketDataProvider`,
this reads FinApp's own normalized schema, not BVB's raw export format. A
later sprint (automatic BVB data updates) will populate a CSV in this shape
from BVB's official dividend announcements.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd

from finapp.application.ports import DividendProvider
from finapp.domain.value_objects.dividend import Dividend
from finapp.domain.value_objects.enums import Currency
from finapp.domain.value_objects.money import Money

REQUIRED_COLUMNS = {"symbol", "amount_per_share", "currency", "pay_date"}


class CsvDividendProvider(DividendProvider):
    """Loads dividend payments from a CSV file with columns: ``symbol``,
    ``amount_per_share``, ``currency``, ``pay_date`` (ISO 8601 date).

    Payments are loaded once at construction, grouped by symbol, and sorted
    by pay date. Call :meth:`refresh` to reload after the underlying file
    changes.
    """

    def __init__(self, csv_path: Path) -> None:
        self._csv_path = csv_path
        self._dividends: dict[str, list[Dividend]] = self._load()

    def _load(self) -> dict[str, list[Dividend]]:
        frame = pd.read_csv(self._csv_path, dtype={"symbol": str, "currency": str})

        missing_columns = REQUIRED_COLUMNS - set(frame.columns)
        if missing_columns:
            raise ValueError(
                f"CSV at {self._csv_path} is missing required columns: "
                f"{sorted(missing_columns)}"
            )

        dividends: dict[str, list[Dividend]] = {}
        for row in frame.itertuples(index=False):
            symbol = str(row.symbol).strip().upper()
            try:
                amount = Decimal(str(row.amount_per_share))
            except InvalidOperation as exc:
                raise ValueError(
                    f"CSV at {self._csv_path}: invalid amount_per_share for symbol "
                    f"'{symbol}': {row.amount_per_share!r}"
                ) from exc

            dividend = Dividend(
                symbol=symbol,
                amount_per_share=Money(
                    amount=amount, currency=Currency(str(row.currency).strip().upper())
                ),
                pay_date=date.fromisoformat(str(row.pay_date).strip()),
            )
            dividends.setdefault(symbol, []).append(dividend)

        for payments in dividends.values():
            payments.sort(key=lambda d: d.pay_date)
        return dividends

    def get_dividends(self, symbol: str) -> Sequence[Dividend]:
        return tuple(self._dividends.get(symbol.strip().upper(), ()))

    def refresh(self) -> None:
        """Reload dividends from disk, e.g. after the CSV cache has been updated."""

        self._dividends = self._load()
