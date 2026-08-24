from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from finapp.application.dto import Quote
from finapp.application.exceptions import PortfolioNotFoundError
from finapp.application.use_cases.run_portfolio_retirement_plan import (
    RunPortfolioRetirementPlan,
)
from finapp.domain.entities.instrument import Instrument
from finapp.domain.entities.portfolio import Portfolio
from finapp.domain.services.retirement_planning import RetirementPlanAssumptions
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


def test_plans_from_current_market_value() -> None:
    tlv = Instrument(
        symbol="TLV", name="Banca Transilvania", currency=Currency.RON, asset_type=AssetType.EQUITY
    )
    portfolio = Portfolio(name="Retirement", base_currency=Currency.RON)
    portfolio.buy(tlv, Decimal("100"), Money(amount=Decimal("4"), currency=Currency.RON))
    repository = InMemoryPortfolioRepository()
    repository.save(portfolio)
    market_data = StaticMarketDataProvider({"TLV": _quote("TLV", "10.00")})  # market value = 1000

    use_case = RunPortfolioRetirementPlan(repository, market_data)
    assumptions = RetirementPlanAssumptions(
        accumulation_years=0,
        accumulation_expected_return=Decimal("0"),
        accumulation_volatility=Decimal("0"),
        retirement_years=1,
        retirement_expected_return=Decimal("0"),
        retirement_volatility=Decimal("0"),
        annual_withdrawal=Decimal("200"),
        simulations=10,
    )
    result = use_case.execute("Retirement", assumptions)

    assert result.portfolio_name == "Retirement"
    assert result.plan.starting_value == Money(amount=Decimal("1000"), currency=Currency.RON)
    assert result.plan.value_at_end_percentile_50 == Money(
        amount=Decimal("800"), currency=Currency.RON
    )
    assert result.plan.probability_of_depletion == Decimal("0")


def test_missing_portfolio_raises() -> None:
    use_case = RunPortfolioRetirementPlan(
        InMemoryPortfolioRepository(), StaticMarketDataProvider({})
    )
    assumptions = RetirementPlanAssumptions(
        accumulation_years=5,
        accumulation_expected_return=Decimal("0.05"),
        accumulation_volatility=Decimal("0.1"),
        retirement_years=20,
        retirement_expected_return=Decimal("0.03"),
        retirement_volatility=Decimal("0.05"),
        annual_withdrawal=Decimal("10000"),
        simulations=100,
    )
    with pytest.raises(PortfolioNotFoundError):
        use_case.execute("Nonexistent", assumptions)
