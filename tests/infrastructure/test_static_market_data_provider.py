from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from finapp.application.dto import Quote
from finapp.application.exceptions import QuoteNotFoundError
from finapp.domain.value_objects.enums import Currency
from finapp.domain.value_objects.money import Money
from finapp.infrastructure.market_data.static_provider import StaticMarketDataProvider


def _quote(symbol: str, amount: str) -> Quote:
    return Quote(
        symbol=symbol,
        price=Money(amount=Decimal(amount), currency=Currency.RON),
        as_of=date(2026, 8, 21),
    )


def test_get_quote_returns_stored_quote() -> None:
    provider = StaticMarketDataProvider({"TLV": _quote("TLV", "4.50")})
    quote = provider.get_quote("tlv")
    assert quote.price.amount == Decimal("4.50")


def test_get_quote_missing_symbol_raises() -> None:
    provider = StaticMarketDataProvider({})
    with pytest.raises(QuoteNotFoundError):
        provider.get_quote("TLV")


def test_get_quotes_bulk() -> None:
    provider = StaticMarketDataProvider(
        {"TLV": _quote("TLV", "4.50"), "SNP": _quote("SNP", "0.55")}
    )
    quotes = provider.get_quotes(["TLV", "SNP"])
    assert quotes["TLV"].price.amount == Decimal("4.50")
    assert quotes["SNP"].price.amount == Decimal("0.55")


def test_symbol_lookup_is_case_insensitive_on_construction_too() -> None:
    provider = StaticMarketDataProvider({"tlv": _quote("TLV", "4.50")})
    assert provider.get_quote("TLV").price.amount == Decimal("4.50")
