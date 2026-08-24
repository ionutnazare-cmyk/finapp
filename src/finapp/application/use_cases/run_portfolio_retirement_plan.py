"""Use case: run a full accumulation + retirement (decumulation) simulation
for a portfolio, starting from its current market value."""

from __future__ import annotations

from finapp.application.dto import PortfolioRetirementPlanResult
from finapp.application.exceptions import PortfolioNotFoundError
from finapp.application.ports import MarketDataProvider, PortfolioRepository
from finapp.application.use_cases.get_portfolio_valuation import GetPortfolioValuation
from finapp.domain.services.retirement_planning import (
    RetirementPlanAssumptions,
    RetirementPlanner,
)


class RunPortfolioRetirementPlan:
    """Project whether a portfolio can sustain retirement withdrawals, by
    running a two-phase (accumulation then decumulation) simulation starting
    from the portfolio's current market value.

    All of the actual math lives in the domain-level
    :class:`~finapp.domain.services.retirement_planning.RetirementPlanner`;
    this use case's only job is obtaining the current starting value (via
    :class:`~finapp.application.use_cases.get_portfolio_valuation.GetPortfolioValuation`)
    and handing it off.
    """

    def __init__(
        self,
        portfolio_repository: PortfolioRepository,
        market_data_provider: MarketDataProvider,
        planner: RetirementPlanner | None = None,
    ) -> None:
        self._portfolio_repository = portfolio_repository
        self._market_data_provider = market_data_provider
        self._planner = planner or RetirementPlanner()

    def execute(
        self, portfolio_name: str, assumptions: RetirementPlanAssumptions
    ) -> PortfolioRetirementPlanResult:
        portfolio = self._portfolio_repository.get(portfolio_name)
        if portfolio is None:
            raise PortfolioNotFoundError(portfolio_name)

        valuation = GetPortfolioValuation(
            self._portfolio_repository, self._market_data_provider
        ).execute(portfolio_name)

        plan = self._planner.plan(valuation.base_currency_total_market_value, assumptions)
        return PortfolioRetirementPlanResult(portfolio_name=portfolio.name, plan=plan)
