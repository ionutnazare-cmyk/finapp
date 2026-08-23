"""A :class:`BonusIssueProvider` backed by a local CSV cache of bonus issues.

Like the market data and dividend CSV adapters, this reads FinApp's own
normalized schema, not BVB's raw announcement format. A later sprint
(automatic BVB data updates) will populate a CSV in this shape from BVB's
official corporate-actions announcements.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd

from finapp.application.ports import BonusIssueProvider
from finapp.domain.value_objects.bonus_issue import BonusIssue

REQUIRED_COLUMNS = {"symbol", "new_shares_per_held_share", "record_date"}


class CsvBonusIssueProvider(BonusIssueProvider):
    """Loads bonus share issues from a CSV file with columns: ``symbol``,
    ``new_shares_per_held_share``, ``record_date`` (ISO 8601 date).

    Events are loaded once at construction, grouped by symbol, and sorted by
    record date. Call :meth:`refresh` to reload after the underlying file
    changes.
    """

    def __init__(self, csv_path: Path) -> None:
        self._csv_path = csv_path
        self._bonus_issues: dict[str, list[BonusIssue]] = self._load()

    def _load(self) -> dict[str, list[BonusIssue]]:
        frame = pd.read_csv(self._csv_path, dtype={"symbol": str})

        missing_columns = REQUIRED_COLUMNS - set(frame.columns)
        if missing_columns:
            raise ValueError(
                f"CSV at {self._csv_path} is missing required columns: "
                f"{sorted(missing_columns)}"
            )

        bonus_issues: dict[str, list[BonusIssue]] = {}
        for row in frame.itertuples(index=False):
            symbol = str(row.symbol).strip().upper()
            try:
                ratio = Decimal(str(row.new_shares_per_held_share))
            except InvalidOperation as exc:
                raise ValueError(
                    f"CSV at {self._csv_path}: invalid new_shares_per_held_share for "
                    f"symbol '{symbol}': {row.new_shares_per_held_share!r}"
                ) from exc

            bonus = BonusIssue(
                symbol=symbol,
                new_shares_per_held_share=ratio,
                record_date=date.fromisoformat(str(row.record_date).strip()),
            )
            bonus_issues.setdefault(symbol, []).append(bonus)

        for issues in bonus_issues.values():
            issues.sort(key=lambda b: b.record_date)
        return bonus_issues

    def get_bonus_issues(self, symbol: str) -> Sequence[BonusIssue]:
        return tuple(self._bonus_issues.get(symbol.strip().upper(), ()))

    def refresh(self) -> None:
        """Reload bonus issues from disk, e.g. after the CSV cache has been updated."""

        self._bonus_issues = self._load()
