from __future__ import annotations

from datetime import date
from decimal import Decimal

from finapp.domain.value_objects.bonus_issue import BonusIssue
from finapp.infrastructure.bonus_issues.static_provider import StaticBonusIssueProvider


def _bonus(symbol: str, ratio: str, record_date: date) -> BonusIssue:
    return BonusIssue(symbol=symbol, new_shares_per_held_share=Decimal(ratio), record_date=record_date)


def test_get_bonus_issues_sorted_by_record_date() -> None:
    provider = StaticBonusIssueProvider(
        {
            "TLV": [
                _bonus("TLV", "0.19", date(2026, 4, 9)),
                _bonus("TLV", "0.17", date(2025, 4, 10)),
            ]
        }
    )
    issues = provider.get_bonus_issues("tlv")
    assert [i.record_date for i in issues] == [date(2025, 4, 10), date(2026, 4, 9)]


def test_get_bonus_issues_missing_symbol_returns_empty() -> None:
    provider = StaticBonusIssueProvider({})
    assert provider.get_bonus_issues("TLV") == ()


def test_get_latest_bonus_issue_returns_most_recent() -> None:
    provider = StaticBonusIssueProvider(
        {
            "TLV": [
                _bonus("TLV", "0.17", date(2025, 4, 10)),
                _bonus("TLV", "0.19", date(2026, 4, 9)),
            ]
        }
    )
    latest = provider.get_latest_bonus_issue("TLV")
    assert latest is not None
    assert latest.new_shares_per_held_share == Decimal("0.19")


def test_get_latest_bonus_issue_none_when_no_history() -> None:
    provider = StaticBonusIssueProvider({})
    assert provider.get_latest_bonus_issue("TLV") is None
