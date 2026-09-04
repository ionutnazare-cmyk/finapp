"""Writes freshly-fetched dividends into the local CSV cache that
:class:`~finapp.infrastructure.dividends.csv_provider.CsvDividendProvider`
reads from — merging with whatever's already there, keyed by symbol and
*year* (not exact date): BVB's page only ever publishes one figure per
year, so a newly-fetched entry replaces any existing row for that same
symbol/year rather than accumulating duplicates.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from pathlib import Path

import pandas as pd

from finapp.application.ports import DividendCacheWriter
from finapp.domain.value_objects.dividend import Dividend

_COLUMNS = ("symbol", "amount_per_share", "currency", "pay_date")


class CsvDividendCacheWriter(DividendCacheWriter):
    """Merges the given dividends into ``csv_path``, keyed by
    (symbol, pay_date.year): an existing row for that symbol/year is
    replaced, a new symbol or year is appended, and rows for other
    symbols/years are left untouched.
    """

    def __init__(self, csv_path: Path) -> None:
        self._csv_path = csv_path

    def save_dividends(self, dividends: Iterable[Dividend]) -> None:
        dividends = list(dividends)
        if not dividends:
            return

        rows: dict[tuple[str, int], dict[str, str]] = {}
        if self._csv_path.exists():
            frame = pd.read_csv(self._csv_path, dtype=str)
            for _, row in frame.iterrows():
                symbol = str(row["symbol"]).strip().upper()
                pay_date = date.fromisoformat(str(row["pay_date"]).strip())
                rows[(symbol, pay_date.year)] = {
                    "symbol": symbol,
                    "amount_per_share": str(row["amount_per_share"]),
                    "currency": str(row["currency"]),
                    "pay_date": pay_date.isoformat(),
                }

        for dividend in dividends:
            rows[(dividend.symbol, dividend.pay_date.year)] = {
                "symbol": dividend.symbol,
                "amount_per_share": str(dividend.amount_per_share.amount),
                "currency": dividend.amount_per_share.currency.value,
                "pay_date": dividend.pay_date.isoformat(),
            }

        self._csv_path.parent.mkdir(parents=True, exist_ok=True)
        ordered = sorted(rows.values(), key=lambda r: (r["symbol"], r["pay_date"]))
        pd.DataFrame(ordered, columns=list(_COLUMNS)).to_csv(self._csv_path, index=False)
