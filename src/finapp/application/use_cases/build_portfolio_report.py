"""Use case: build the aggregated data behind a portfolio report."""

from __future__ import annotations

from datetime import UTC, datetime

from finapp.application.dto import PortfolioReport
from finapp.application.ports import DividendProvider, MarketDataProvider, PortfolioRepository
from finapp.application.use_cases.get_portfolio_dividend_income import (
    GetPortfolioDividendIncome,
)
from finapp.application.use_cases.get_portfolio_valuation import GetPortfolioValuation


class BuildPortfolioReport:
    """Aggregates a portfolio's valuation and (optionally) dividend income
    into a single :class:`~finapp.application.dto.PortfolioReport`, ready to
    hand to an Excel or PDF exporter.

    Building this once and sharing it between both export formats
    guarantees their figures always agree — there's no way for an Excel
    export and a PDF export of the same portfolio to disagree with each
    other, since both render from the same already-computed report.
    """

    def __init__(
        self,
        portfolio_repository: PortfolioRepository,
        market_data_provider: MarketDataProvider,
        dividend_provider: DividendProvider | None = None,
    ) -> None:
        self._portfolio_repository = portfolio_repository
        self._market_data_provider = market_data_provider
        self._dividend_provider = dividend_provider

    def execute(self, portfolio_name: str, include_dividend_income: bool = True) -> PortfolioReport:
        valuation = GetPortfolioValuation(
            self._portfolio_repository, self._market_data_provider
        ).execute(portfolio_name)

        dividend_income = None
        if include_dividend_income and self._dividend_provider is not None:
            dividend_income = GetPortfolioDividendIncome(
                self._portfolio_repository, self._dividend_provider
            ).execute(portfolio_name)

        return PortfolioReport(
            portfolio_name=portfolio_name,
            generated_at=datetime.now(UTC),
            valuation=valuation,
            dividend_income=dividend_income,
        )
