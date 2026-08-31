"""Domain services: stateless business/quantitative logic that doesn't
naturally belong to a single entity or value object.

Like the rest of the domain layer, no I/O and no dependency on application
ports — see ``docs/ARCHITECTURE.md``.

- ``finapp.domain.services.monte_carlo``: ``MonteCarloAssumptions``,
  ``MonteCarloResult``, ``MonteCarloSimulator``.
- ``finapp.domain.services.portfolio_optimizer``: ``OptimizationInput``,
  ``OptimizedAllocation``, ``OptimizationResult``, ``PortfolioOptimizer``.
- ``finapp.domain.services.retirement_planning``: ``RetirementPlanAssumptions``,
  ``RetirementPlanResult``, ``RetirementPlanner``.
- ``finapp.domain.services.fair_value``: ``FairValueEstimate``,
  ``FairValueEstimator``.
- ``finapp.domain.services.dividend_safety``: ``DividendSafetyInputs``,
  ``DividendSafetyScore``, ``DividendSafetyScoreComponent``,
  ``DividendSafetyRating``, ``DividendSafetyScorer``.
- ``finapp.domain.services.data_freshness``: ``DataFreshnessPolicy``.
"""

from __future__ import annotations

from finapp.domain.services.data_freshness import DataFreshnessPolicy
from finapp.domain.services.dividend_safety import (
    DividendSafetyInputs,
    DividendSafetyRating,
    DividendSafetyScore,
    DividendSafetyScoreComponent,
    DividendSafetyScorer,
)
from finapp.domain.services.fair_value import FairValueEstimate, FairValueEstimator
from finapp.domain.services.monte_carlo import (
    MonteCarloAssumptions,
    MonteCarloResult,
    MonteCarloSimulator,
)
from finapp.domain.services.portfolio_optimizer import (
    OptimizationInput,
    OptimizationResult,
    OptimizedAllocation,
    PortfolioOptimizer,
)
from finapp.domain.services.retirement_planning import (
    RetirementPlanAssumptions,
    RetirementPlanner,
    RetirementPlanResult,
)

__all__ = [
    "DataFreshnessPolicy",
    "DividendSafetyInputs",
    "DividendSafetyRating",
    "DividendSafetyScore",
    "DividendSafetyScoreComponent",
    "DividendSafetyScorer",
    "FairValueEstimate",
    "FairValueEstimator",
    "MonteCarloAssumptions",
    "MonteCarloResult",
    "MonteCarloSimulator",
    "OptimizationInput",
    "OptimizationResult",
    "OptimizedAllocation",
    "PortfolioOptimizer",
    "RetirementPlanAssumptions",
    "RetirementPlanResult",
    "RetirementPlanner",
]
