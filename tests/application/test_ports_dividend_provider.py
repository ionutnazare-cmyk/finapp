from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from finapp.application.ports import DividendProvider
from finapp.domain.value_objects.dividend import Dividend
from finapp.domain.value_objects.enums import Currency
from finapp.domain.value_objects.money import Money


def test_dividend_provider_cannot_be_instantiated_directly() -> None:
    with pytest.raises(TypeError):
        DividendProvider()  # type: ignore[abstract]


class _FakeProvider(DividendProvider):
    def __init__(self) -> None:
        self._history = [
            Dividend(
                symbol="TLV",
                amount_per_share=Money(amount=Decimal("0.22"), currency=Currency.RON),
                pay_date=date(2025, 6, 15),
            ),
            Dividend(
                symbol="TLV",
                amount_per_share=Money(amount=Decimal("0.25"), currency=Currency.RON),
                pay_date=date(2026, 6, 14),
            ),
        ]

    def get_dividends(self, symbol: str) -> tuple[Dividend, ...]:
        return tuple(self._history) if symbol.upper() == "TLV" else ()


def test_default_get_latest_dividend_returns_last_item() -> None:
    provider = _FakeProvider()
    latest = provider.get_latest_dividend("TLV")
    assert latest is not None
    assert latest.amount_per_share.amount == Decimal("0.25")


def test_default_get_latest_dividend_none_when_empty() -> None:
    provider = _FakeProvider()
    assert provider.get_latest_dividend("SNP") is None
