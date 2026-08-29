from __future__ import annotations

from datetime import date
from decimal import Decimal

from finapp.application.dto import Quote
from finapp.application.use_cases.build_portfolio_report import BuildPortfolioReport
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


def _quote(symbol: str, amount: str) -> Quote:
    return Quote(
        symbol=symbol,
        price=Money(amount=Decimal(amount), currency=Currency.RON),
        as_of=date(2026, 8, 21),
    )


def _repository_with_tlv() -> InMemoryPortfolioRepository:
    tlv = Instrument(
        symbol="TLV", name="Banca Transilvania", currency=Currency.RON, asset_type=AssetType.EQUITY
    )
    portfolio = Portfolio(name="Retirement", base_currency=Currency.RON)
    portfolio.buy(tlv, Decimal("100"), Money(amount=Decimal("4"), currency=Currency.RON))
    repository = InMemoryPortfolioRepository()
    repository.save(portfolio)
    return repository


def test_report_includes_valuation() -> None:
    repository = _repository_with_tlv()
    market_data = StaticMarketDataProvider({"TLV": _quote("TLV", "4.50")})
    builder = BuildPortfolioReport(repository, market_data)

    report = builder.execute("Retirement")

    assert report.portfolio_name == "Retirement"
    assert report.valuation.base_currency_total_market_value == Money(
        amount=Decimal("450"), currency=Currency.RON
    )
    assert report.generated_at is not None


def test_report_includes_dividend_income_when_provider_given() -> None:
    repository = _repository_with_tlv()
    market_data = StaticMarketDataProvider({"TLV": _quote("TLV", "4.50")})
    dividends = StaticDividendProvider(
        {
            "TLV": [
                Dividend(
                    symbol="TLV",
                    amount_per_share=Money(amount=Decimal("0.25"), currency=Currency.RON),
                    pay_date=date(2026, 6, 14),
                )
            ]
        }
    )
    builder = BuildPortfolioReport(repository, market_data, dividends)

    report = builder.execute("Retirement")

    assert report.dividend_income is not None
    assert report.dividend_income.base_currency_total_income == Money(
        amount=Decimal("25.00"), currency=Currency.RON
    )


def test_report_omits_dividend_income_without_provider() -> None:
    repository = _repository_with_tlv()
    market_data = StaticMarketDataProvider({"TLV": _quote("TLV", "4.50")})
    builder = BuildPortfolioReport(repository, market_data)

    report = builder.execute("Retirement")

    assert report.dividend_income is None


def test_report_omits_dividend_income_when_excluded_explicitly() -> None:
    repository = _repository_with_tlv()
    market_data = StaticMarketDataProvider({"TLV": _quote("TLV", "4.50")})
    dividends = StaticDividendProvider({})
    builder = BuildPortfolioReport(repository, market_data, dividends)

    report = builder.execute("Retirement", include_dividend_income=False)

    assert report.dividend_income is None
