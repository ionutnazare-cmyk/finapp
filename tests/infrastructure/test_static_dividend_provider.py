from __future__ import annotations

from datetime import date
from decimal import Decimal

from finapp.domain.value_objects.dividend import Dividend
from finapp.domain.value_objects.enums import Currency
from finapp.domain.value_objects.money import Money
from finapp.infrastructure.dividends.static_provider import StaticDividendProvider


def _dividend(symbol: str, amount: str, pay_date: date) -> Dividend:
    return Dividend(
        symbol=symbol,
        amount_per_share=Money(amount=Decimal(amount), currency=Currency.RON),
        pay_date=pay_date,
    )


def test_get_dividends_returns_stored_history_sorted_by_date() -> None:
    provider = StaticDividendProvider(
        {
            "TLV": [
                _dividend("TLV", "0.25", date(2026, 6, 14)),
                _dividend("TLV", "0.22", date(2025, 6, 15)),
            ]
        }
    )
    dividends = provider.get_dividends("tlv")
    assert [d.pay_date for d in dividends] == [date(2025, 6, 15), date(2026, 6, 14)]


def test_get_dividends_missing_symbol_returns_empty() -> None:
    provider = StaticDividendProvider({})
    assert provider.get_dividends("TLV") == ()


def test_get_latest_dividend_returns_most_recent() -> None:
    provider = StaticDividendProvider(
        {
            "TLV": [
                _dividend("TLV", "0.22", date(2025, 6, 15)),
                _dividend("TLV", "0.25", date(2026, 6, 14)),
            ]
        }
    )
    latest = provider.get_latest_dividend("TLV")
    assert latest is not None
    assert latest.amount_per_share.amount == Decimal("0.25")


def test_get_latest_dividend_none_when_no_history() -> None:
    provider = StaticDividendProvider({})
    assert provider.get_latest_dividend("TLV") is None
