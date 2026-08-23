"""Domain services: stateless business/quantitative logic that doesn't
naturally belong to a single entity or value object.

Like the rest of the domain layer, no I/O and no dependency on application
ports — see ``docs/ARCHITECTURE.md``.

- ``finapp.domain.services.monte_carlo``: ``MonteCarloAssumptions``,
  ``MonteCarloResult``, ``MonteCarloSimulator``.
- ``finapp.domain.services.portfolio_optimizer``: ``OptimizationInput``,
  ``OptimizedAllocation``, ``OptimizationResult``, ``PortfolioOptimizer``.
"""

from __future__ import annotations

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

__all__ = [
    "MonteCarloAssumptions",
    "MonteCarloResult",
    "MonteCarloSimulator",
    "OptimizationInput",
    "OptimizationResult",
    "OptimizedAllocation",
    "PortfolioOptimizer",
]
