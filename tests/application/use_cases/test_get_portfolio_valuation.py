from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from finapp.application.dto import Quote
from finapp.application.exceptions import PortfolioNotFoundError, QuoteNotFoundError
from finapp.application.use_cases.get_portfolio_valuation import GetPortfolioValuation
from finapp.domain.entities.instrument import Instrument
from finapp.domain.entities.portfolio import Portfolio
from finapp.domain.value_objects.enums import AssetType, Currency
from finapp.domain.value_objects.money import Money
from finapp.infrastructure.market_data.static_provider import StaticMarketDataProvider
from finapp.infrastructure.repositories.in_memory_portfolio_repository import (
    InMemoryPortfolioRepository,
)


def _quote(symbol: str, amount: str) -> Quote:
    return Quote(
        symbol=symbol,
        price=Money(amount=Decimal(amount), currency=Currency.RON),
        as_of=date(2026, 8, 21),
    )


@pytest.fixture
def populated_repository() -> InMemoryPortfolioRepository:
    tlv = Instrument(
        symbol="TLV",
        name="Banca Transilvania",
        currency=Currency.RON,
        asset_type=AssetType.EQUITY,
    )
    snp = Instrument(
        symbol="SNP", name="OMV Petrom", currency=Currency.RON, asset_type=AssetType.EQUITY
    )
    portfolio = Portfolio(name="Retirement", base_currency=Currency.RON)
    portfolio.buy(tlv, Decimal("100"), Money(amount=Decimal("4"), currency=Currency.RON))
    portfolio.buy(snp, Decimal("1000"), Money(amount=Decimal("0.50"), currency=Currency.RON))
    repository = InMemoryPortfolioRepository()
    repository.save(portfolio)
    return repository


def test_valuation_totals_and_breakdown(populated_repository: InMemoryPortfolioRepository) -> None:
    market_data = StaticMarketDataProvider(
        {"TLV": _quote("TLV", "4.50"), "SNP": _quote("SNP", "0.60")}
    )
    use_case = GetPortfolioValuation(populated_repository, market_data)

    valuation = use_case.execute("Retirement")

    assert valuation.portfolio_name == "Retirement"
    assert valuation.base_currency_total_book_cost == Money(
        amount=Decimal("900"), currency=Currency.RON
    )
    assert valuation.base_currency_total_market_value == Money(
        amount=Decimal("1050"), currency=Currency.RON
    )
    assert valuation.base_currency_total_unrealized_pnl == Money(
        amount=Decimal("150"), currency=Currency.RON
    )
    assert len(valuation.positions) == 2
    by_symbol = {p.symbol: p for p in valuation.positions}
    assert by_symbol["TLV"].market_value == Money(amount=Decimal("450"), currency=Currency.RON)
    assert by_symbol["SNP"].unrealized_pnl == Money(amount=Decimal("100"), currency=Currency.RON)


def test_valuation_of_empty_portfolio_is_zero() -> None:
    repository = InMemoryPortfolioRepository()
    repository.save(Portfolio(name="Empty", base_currency=Currency.RON))
    use_case = GetPortfolioValuation(repository, StaticMarketDataProvider({}))

    valuation = use_case.execute("Empty")

    assert valuation.base_currency_total_book_cost.is_zero()
    assert valuation.base_currency_total_market_value.is_zero()
    assert valuation.positions == ()


def test_missing_portfolio_raises(populated_repository: InMemoryPortfolioRepository) -> None:
    use_case = GetPortfolioValuation(populated_repository, StaticMarketDataProvider({}))
    with pytest.raises(PortfolioNotFoundError):
        use_case.execute("Nonexistent")


def test_missing_quote_raises(populated_repository: InMemoryPortfolioRepository) -> None:
    market_data = StaticMarketDataProvider({"TLV": _quote("TLV", "4.50")})
    use_case = GetPortfolioValuation(populated_repository, market_data)
    with pytest.raises(QuoteNotFoundError):
        use_case.execute("Retirement")
