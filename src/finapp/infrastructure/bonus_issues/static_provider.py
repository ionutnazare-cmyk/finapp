"""An in-memory :class:`BonusIssueProvider` backed by a fixed mapping of bonus issues."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from finapp.application.ports import BonusIssueProvider
from finapp.domain.value_objects.bonus_issue import BonusIssue


class StaticBonusIssueProvider(BonusIssueProvider):
    """A :class:`BonusIssueProvider` backed by an in-memory mapping of bonus
    issue events per symbol, sorted by record date.

    Useful for unit tests, demos, and manual overrides before a live BVB
    corporate-actions feed is wired in.
    """

    def __init__(self, bonus_issues: Mapping[str, Sequence[BonusIssue]]) -> None:
        self._bonus_issues: dict[str, list[BonusIssue]] = {
            symbol.strip().upper(): sorted(issues, key=lambda b: b.record_date)
            for symbol, issues in bonus_issues.items()
        }

    def get_bonus_issues(self, symbol: str) -> Sequence[BonusIssue]:
        return tuple(self._bonus_issues.get(symbol.strip().upper(), ()))
