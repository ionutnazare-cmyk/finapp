"""Use case: run a mean-variance portfolio optimization."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from finapp.domain.services.portfolio_optimizer import (
    OptimizationInput,
    OptimizationResult,
    PortfolioOptimizer,
)


class OptimizationObjective(StrEnum):
    """Which mean-variance objective to solve for."""

    MAXIMIZE_SHARPE_RATIO = "MAXIMIZE_SHARPE_RATIO"
    MINIMIZE_VOLATILITY = "MINIMIZE_VOLATILITY"


class OptimizePortfolio:
    """Run a mean-variance optimization for a chosen objective.

    Unlike most other use cases, this one has no repository or port
    dependency: its inputs (expected returns, covariance) are assumptions
    supplied by the caller, not derived from a stored portfolio — there's
    no historical-return data source yet (that arrives with automatic BVB
    data updates, a later sprint). It's still routed through ``application``
    rather than having the presentation layer call
    :mod:`finapp.domain.services.portfolio_optimizer` directly, keeping the
    layering consistent even though this wrapper is thin.
    """

    def __init__(self, optimizer: PortfolioOptimizer | None = None) -> None:
        self._optimizer = optimizer or PortfolioOptimizer()

    def execute(
        self,
        inputs: OptimizationInput,
        objective: OptimizationObjective = OptimizationObjective.MAXIMIZE_SHARPE_RATIO,
        target_return: Decimal | None = None,
    ) -> OptimizationResult:
        if objective == OptimizationObjective.MAXIMIZE_SHARPE_RATIO:
            return self._optimizer.maximize_sharpe_ratio(inputs)
        return self._optimizer.minimize_volatility(inputs, target_return=target_return)
