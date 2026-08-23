from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from finapp.application.dto import Quote
from finapp.application.exceptions import PortfolioNotFoundError
from finapp.application.use_cases.run_portfolio_monte_carlo_simulation import (
    RunPortfolioMonteCarloSimulation,
)
from finapp.domain.entities.instrument import Instrument
from finapp.domain.entities.portfolio import Portfolio
from finapp.domain.services.monte_carlo import MonteCarloAssumptions
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


def test_simulates_from_current_market_value() -> None:
    tlv = Instrument(
        symbol="TLV", name="Banca Transilvania", currency=Currency.RON, asset_type=AssetType.EQUITY
    )
    portfolio = Portfolio(name="Retirement", base_currency=Currency.RON)
    portfolio.buy(tlv, Decimal("100"), Money(amount=Decimal("4"), currency=Currency.RON))
    repository = InMemoryPortfolioRepository()
    repository.save(portfolio)
    market_data = StaticMarketDataProvider({"TLV": _quote("TLV", "5.00")})  # market value = 500

    use_case = RunPortfolioMonteCarloSimulation(repository, market_data)
    assumptions = MonteCarloAssumptions(
        expected_annual_return=Decimal("0"),
        annual_volatility=Decimal("0"),
        years=3,
        simulations=10,
    )
    result = use_case.execute("Retirement", assumptions)

    assert result.portfolio_name == "Retirement"
    assert result.simulation.starting_value == Money(amount=Decimal("500"), currency=Currency.RON)
    assert result.simulation.mean == Money(amount=Decimal("500"), currency=Currency.RON)


def test_empty_portfolio_simulates_from_zero() -> None:
    repository = InMemoryPortfolioRepository()
    repository.save(Portfolio(name="Empty", base_currency=Currency.RON))
    use_case = RunPortfolioMonteCarloSimulation(repository, StaticMarketDataProvider({}))
    assumptions = MonteCarloAssumptions(
        expected_annual_return=Decimal("0.05"),
        annual_volatility=Decimal("0"),
        years=5,
        simulations=10,
    )
    result = use_case.execute("Empty", assumptions)
    assert result.simulation.starting_value.is_zero()
    assert result.simulation.mean.is_zero()


def test_missing_portfolio_raises() -> None:
    use_case = RunPortfolioMonteCarloSimulation(
        InMemoryPortfolioRepository(), StaticMarketDataProvider({})
    )
    assumptions = MonteCarloAssumptions(
        expected_annual_return=Decimal("0.05"),
        annual_volatility=Decimal("0.1"),
        years=10,
        simulations=100,
    )
    with pytest.raises(PortfolioNotFoundError):
        use_case.execute("Nonexistent", assumptions)
