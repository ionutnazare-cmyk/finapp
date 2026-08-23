from __future__ import annotations

from decimal import Decimal

import pytest

from finapp.application.use_cases.optimize_portfolio import (
    OptimizationObjective,
    OptimizePortfolio,
)
from finapp.domain.services.portfolio_optimizer import OptimizationInput


@pytest.fixture
def inputs() -> OptimizationInput:
    return OptimizationInput(
        symbols=("A", "B"),
        expected_returns=(Decimal("0.08"), Decimal("0.05")),
        covariance_matrix=(
            (Decimal("0.04"), Decimal("0")),
            (Decimal("0"), Decimal("0.01")),
        ),
    )


def test_defaults_to_maximize_sharpe_ratio(inputs: OptimizationInput) -> None:
    use_case = OptimizePortfolio()
    result = use_case.execute(inputs)
    weights = {a.symbol: float(a.weight) for a in result.allocations}
    assert sum(weights.values()) == pytest.approx(1.0, abs=1e-6)


def test_minimize_volatility_objective_matches_analytical_solution(
    inputs: OptimizationInput,
) -> None:
    use_case = OptimizePortfolio()
    result = use_case.execute(inputs, objective=OptimizationObjective.MINIMIZE_VOLATILITY)
    weights = {a.symbol: float(a.weight) for a in result.allocations}
    assert weights["A"] == pytest.approx(0.2, abs=1e-3)
    assert weights["B"] == pytest.approx(0.8, abs=1e-3)


def test_minimize_volatility_with_target_return(inputs: OptimizationInput) -> None:
    use_case = OptimizePortfolio()
    result = use_case.execute(
        inputs,
        objective=OptimizationObjective.MINIMIZE_VOLATILITY,
        target_return=Decimal("0.065"),
    )
    assert float(result.expected_return) == pytest.approx(0.065, abs=1e-3)
