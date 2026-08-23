"""Use case: project a portfolio's future value via Monte Carlo simulation."""

from __future__ import annotations

from finapp.application.dto import PortfolioMonteCarloResult
from finapp.application.exceptions import PortfolioNotFoundError
from finapp.application.ports import MarketDataProvider, PortfolioRepository
from finapp.application.use_cases.get_portfolio_valuation import GetPortfolioValuation
from finapp.domain.services.monte_carlo import MonteCarloAssumptions, MonteCarloSimulator


class RunPortfolioMonteCarloSimulation:
    """Project a portfolio's future value by running a Monte Carlo simulation
    starting from its current market value.

    All of the actual math lives in the domain-level
    :class:`~finapp.domain.services.monte_carlo.MonteCarloSimulator`; this
    use case's only job is obtaining the current starting value (via
    :class:`~finapp.application.use_cases.get_portfolio_valuation.GetPortfolioValuation`)
    and handing it off. An empty portfolio simulates from a starting value
    of zero, which is a valid (if not very interesting) result, not an error.
    """

    def __init__(
        self,
        portfolio_repository: PortfolioRepository,
        market_data_provider: MarketDataProvider,
        simulator: MonteCarloSimulator | None = None,
    ) -> None:
        self._portfolio_repository = portfolio_repository
        self._market_data_provider = market_data_provider
        self._simulator = simulator or MonteCarloSimulator()

    def execute(
        self, portfolio_name: str, assumptions: MonteCarloAssumptions
    ) -> PortfolioMonteCarloResult:
        portfolio = self._portfolio_repository.get(portfolio_name)
        if portfolio is None:
            raise PortfolioNotFoundError(portfolio_name)

        valuation = GetPortfolioValuation(
            self._portfolio_repository, self._market_data_provider
        ).execute(portfolio_name)

        simulation = self._simulator.simulate(
            valuation.base_currency_total_market_value, assumptions
        )
        return PortfolioMonteCarloResult(portfolio_name=portfolio.name, simulation=simulation)
