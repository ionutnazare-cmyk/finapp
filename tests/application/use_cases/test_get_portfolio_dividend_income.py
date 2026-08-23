from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from finapp.application.exceptions import PortfolioNotFoundError
from finapp.application.use_cases.get_portfolio_dividend_income import (
    GetPortfolioDividendIncome,
)
from finapp.domain.entities.instrument import Instrument
from finapp.domain.entities.portfolio import Portfolio
from finapp.domain.exceptions import CurrencyMismatchError
from finapp.domain.value_objects.dividend import Dividend
from finapp.domain.value_objects.enums import AssetType, Currency
from finapp.domain.value_objects.money import Money
from finapp.infrastructure.dividends.static_provider import StaticDividendProvider
from finapp.infrastructure.repositories.in_memory_portfolio_repository import (
    InMemoryPortfolioRepository,
)


def _dividend(symbol: str, amount: str, currency: Currency = Currency.RON) -> Dividend:
    return Dividend(
        symbol=symbol,
        amount_per_share=Money(amount=Decimal(amount), currency=currency),
        pay_date=date(2026, 6, 14),
    )


@pytest.fixture
def repository() -> InMemoryPortfolioRepository:
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
    portfolio.buy(tlv, Decimal("200"), Money(amount=Decimal("4"), currency=Currency.RON))
    portfolio.buy(snp, Decimal("1000"), Money(amount=Decimal("0.50"), currency=Currency.RON))
    repository = InMemoryPortfolioRepository()
    repository.save(portfolio)
    return repository


def test_computes_income_only_for_positions_with_known_dividends(
    repository: InMemoryPortfolioRepository,
) -> None:
    dividends = StaticDividendProvider({"TLV": [_dividend("TLV", "0.25")]})
    use_case = GetPortfolioDividendIncome(repository, dividends)

    result = use_case.execute("Retirement")

    assert len(result.incomes) == 1
    assert result.incomes[0].instrument.symbol == "TLV"
    assert result.incomes[0].total_income == Money(amount=Decimal("50.00"), currency=Currency.RON)
    assert result.base_currency_total_income == Money(
        amount=Decimal("50.00"), currency=Currency.RON
    )


def test_no_known_dividends_gives_zero_income(
    repository: InMemoryPortfolioRepository,
) -> None:
    use_case = GetPortfolioDividendIncome(repository, StaticDividendProvider({}))
    result = use_case.execute("Retirement")
    assert result.incomes == ()
    assert result.base_currency_total_income.is_zero()


def test_missing_portfolio_raises() -> None:
    use_case = GetPortfolioDividendIncome(InMemoryPortfolioRepository(), StaticDividendProvider({}))
    with pytest.raises(PortfolioNotFoundError):
        use_case.execute("Nonexistent")


def test_currency_mismatch_propagates(repository: InMemoryPortfolioRepository) -> None:
    dividends = StaticDividendProvider({"TLV": [_dividend("TLV", "0.25", Currency.USD)]})
    use_case = GetPortfolioDividendIncome(repository, dividends)
    with pytest.raises(CurrencyMismatchError):
        use_case.execute("Retirement")
