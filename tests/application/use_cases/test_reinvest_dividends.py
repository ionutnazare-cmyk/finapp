from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from finapp.application.dto import Quote
from finapp.application.exceptions import PortfolioNotFoundError, QuoteNotFoundError
from finapp.application.use_cases.reinvest_dividends import ReinvestDividends
from finapp.domain.entities.instrument import Instrument
from finapp.domain.entities.portfolio import Portfolio
from finapp.domain.value_objects.dividend import Dividend
from finapp.domain.value_objects.enums import AssetType, Currency
from finapp.domain.value_objects.money import Money
from finapp.infrastructure.dividends.static_provider import StaticDividendProvider
from finapp.infrastructure.market_data.static_provider import StaticMarketDataProvider
from finapp.infrastructure.repositories.in_memory_portfolio_repository import (
    InMemoryPortfolioRepository,
)


def _dividend(symbol: str, amount: str) -> Dividend:
    return Dividend(
        symbol=symbol,
        amount_per_share=Money(amount=Decimal(amount), currency=Currency.RON),
        pay_date=date(2026, 6, 14),
    )


def _quote(symbol: str, amount: str) -> Quote:
    return Quote(
        symbol=symbol,
        price=Money(amount=Decimal(amount), currency=Currency.RON),
        as_of=date(2026, 8, 21),
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


def test_reinvests_dividend_income_into_more_shares(
    repository: InMemoryPortfolioRepository,
) -> None:
    dividends = StaticDividendProvider({"TLV": [_dividend("TLV", "0.25")]})
    market_data = StaticMarketDataProvider({"TLV": _quote("TLV", "5.00")})
    use_case = ReinvestDividends(repository, dividends, market_data)

    result = use_case.execute("Retirement")

    # 200 shares * 0.25 = 50 RON dividend income -> 50 / 5.00 = 10 new shares
    assert len(result.reinvestments) == 1
    assert result.reinvestments[0].instrument.symbol == "TLV"
    assert result.reinvestments[0].dividend_income == Money(
        amount=Decimal("50.00"), currency=Currency.RON
    )
    assert result.reinvestments[0].quantity_purchased == Decimal("10.00")
    assert result.base_currency_total_reinvested == Money(
        amount=Decimal("50.00"), currency=Currency.RON
    )

    stored = repository.get("Retirement")
    assert stored is not None
    position = stored.get_position("TLV")
    assert position is not None
    assert position.quantity == Decimal("210.00")


def test_positions_without_known_dividend_are_skipped(
    repository: InMemoryPortfolioRepository,
) -> None:
    use_case = ReinvestDividends(
        repository, StaticDividendProvider({}), StaticMarketDataProvider({})
    )
    result = use_case.execute("Retirement")
    assert result.reinvestments == ()
    assert result.base_currency_total_reinvested.is_zero()


def test_missing_portfolio_raises() -> None:
    use_case = ReinvestDividends(
        InMemoryPortfolioRepository(), StaticDividendProvider({}), StaticMarketDataProvider({})
    )
    with pytest.raises(PortfolioNotFoundError):
        use_case.execute("Nonexistent")


def test_missing_quote_for_dividend_paying_position_raises(
    repository: InMemoryPortfolioRepository,
) -> None:
    dividends = StaticDividendProvider({"TLV": [_dividend("TLV", "0.25")]})
    use_case = ReinvestDividends(repository, dividends, StaticMarketDataProvider({}))
    with pytest.raises(QuoteNotFoundError):
        use_case.execute("Retirement")
