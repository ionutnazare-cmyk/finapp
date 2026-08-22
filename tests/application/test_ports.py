from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from finapp.application.dto import Quote
from finapp.application.exceptions import QuoteNotFoundError
from finapp.application.ports import MarketDataProvider
from finapp.domain.value_objects.enums import Currency
from finapp.domain.value_objects.money import Money


class _FakeProvider(MarketDataProvider):
    """Minimal concrete provider used to exercise the port's default behavior."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def get_quote(self, symbol: str) -> Quote:
        self.calls.append(symbol)
        if symbol == "MISSING":
            raise QuoteNotFoundError(symbol)
        return Quote(
            symbol=symbol,
            price=Money(amount=Decimal("1"), currency=Currency.RON),
            as_of=date(2026, 1, 1),
        )


def test_market_data_provider_cannot_be_instantiated_directly() -> None:
    with pytest.raises(TypeError):
        MarketDataProvider()  # type: ignore[abstract]


def test_default_get_quotes_delegates_to_get_quote_per_symbol() -> None:
    provider = _FakeProvider()
    quotes = provider.get_quotes(["TLV", "SNP"])
    assert set(quotes) == {"TLV", "SNP"}
    assert provider.calls == ["TLV", "SNP"]


def test_get_quote_propagates_not_found() -> None:
    provider = _FakeProvider()
    with pytest.raises(QuoteNotFoundError):
        provider.get_quote("MISSING")
