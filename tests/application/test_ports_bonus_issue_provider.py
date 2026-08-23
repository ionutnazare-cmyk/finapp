from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from finapp.application.ports import BonusIssueProvider
from finapp.domain.value_objects.bonus_issue import BonusIssue


def test_bonus_issue_provider_cannot_be_instantiated_directly() -> None:
    with pytest.raises(TypeError):
        BonusIssueProvider()  # type: ignore[abstract]


class _FakeProvider(BonusIssueProvider):
    def __init__(self) -> None:
        self._history = [
            BonusIssue(
                symbol="TLV", new_shares_per_held_share=Decimal("0.17"), record_date=date(2025, 4, 10)
            ),
            BonusIssue(
                symbol="TLV", new_shares_per_held_share=Decimal("0.19"), record_date=date(2026, 4, 9)
            ),
        ]

    def get_bonus_issues(self, symbol: str) -> tuple[BonusIssue, ...]:
        return tuple(self._history) if symbol.upper() == "TLV" else ()


def test_default_get_latest_bonus_issue_returns_last_item() -> None:
    provider = _FakeProvider()
    latest = provider.get_latest_bonus_issue("TLV")
    assert latest is not None
    assert latest.new_shares_per_held_share == Decimal("0.19")


def test_default_get_latest_bonus_issue_none_when_empty() -> None:
    provider = _FakeProvider()
    assert provider.get_latest_bonus_issue("SNP") is None
