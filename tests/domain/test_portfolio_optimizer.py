from __future__ import annotations

from decimal import Decimal

import pytest

from finapp.domain.services.portfolio_optimizer import (
    OptimizationInput,
    PortfolioOptimizer,
)


def test_minimum_variance_matches_analytical_solution_for_uncorrelated_assets() -> None:
    # Two uncorrelated assets: var_A=0.04, var_B=0.01.
    # Analytical minimum-variance weight: w_A = var_B / (var_A + var_B) = 0.2
    inputs = OptimizationInput(
        symbols=("A", "B"),
        expected_returns=(Decimal("0.08"), Decimal("0.05")),
        covariance_matrix=(
            (Decimal("0.04"), Decimal("0")),
            (Decimal("0"), Decimal("0.01")),
        ),
    )
    result = PortfolioOptimizer().minimize_volatility(inputs)

    weights = {a.symbol: float(a.weight) for a in result.allocations}
    assert weights["A"] == pytest.approx(0.2, abs=1e-3)
    assert weights["B"] == pytest.approx(0.8, abs=1e-3)
    assert sum(weights.values()) == pytest.approx(1.0, abs=1e-6)


def test_maximize_sharpe_prefers_only_the_positive_return_asset() -> None:
    # Equal volatility, zero correlation, B has negative expected return:
    # with no diversification benefit and no way to short B, the
    # Sharpe-maximizing long-only portfolio is 100% A.
    inputs = OptimizationInput(
        symbols=("A", "B"),
        expected_returns=(Decimal("0.10"), Decimal("-0.05")),
        covariance_matrix=(
            (Decimal("0.04"), Decimal("0")),
            (Decimal("0"), Decimal("0.04")),
        ),
    )
    result = PortfolioOptimizer().maximize_sharpe_ratio(inputs)

    weights = {a.symbol: float(a.weight) for a in result.allocations}
    assert weights["A"] == pytest.approx(1.0, abs=1e-3)
    assert weights["B"] == pytest.approx(0.0, abs=1e-3)
    assert float(result.expected_return) == pytest.approx(0.10, abs=1e-3)
    assert float(result.expected_volatility) == pytest.approx(0.20, abs=1e-3)
    assert float(result.sharpe_ratio) == pytest.approx(0.5, abs=1e-2)


def test_minimize_volatility_with_target_return_constraint() -> None:
    inputs = OptimizationInput(
        symbols=("A", "B"),
        expected_returns=(Decimal("0.10"), Decimal("0.04")),
        covariance_matrix=(
            (Decimal("0.04"), Decimal("0")),
            (Decimal("0"), Decimal("0.01")),
        ),
    )
    result = PortfolioOptimizer().minimize_volatility(inputs, target_return=Decimal("0.07"))

    assert float(result.expected_return) == pytest.approx(0.07, abs=1e-3)
    weights = {a.symbol: float(a.weight) for a in result.allocations}
    assert sum(weights.values()) == pytest.approx(1.0, abs=1e-6)


def test_weights_are_non_negative_and_sum_to_one() -> None:
    inputs = OptimizationInput(
        symbols=("A", "B", "C"),
        expected_returns=(Decimal("0.06"), Decimal("0.08"), Decimal("0.05")),
        covariance_matrix=(
            (Decimal("0.02"), Decimal("0.005"), Decimal("0.0")),
            (Decimal("0.005"), Decimal("0.03"), Decimal("0.002")),
            (Decimal("0.0"), Decimal("0.002"), Decimal("0.015")),
        ),
    )
    result = PortfolioOptimizer().maximize_sharpe_ratio(inputs)

    total = sum(float(a.weight) for a in result.allocations)
    assert total == pytest.approx(1.0, abs=1e-6)
    assert all(float(a.weight) >= 0.0 for a in result.allocations)


def test_too_few_symbols_rejected() -> None:
    with pytest.raises(Exception):  # noqa: B017 - pydantic ValidationError
        OptimizationInput(
            symbols=("A",),
            expected_returns=(Decimal("0.05"),),
            covariance_matrix=((Decimal("0.04"),),),
        )


def test_mismatched_expected_returns_length_rejected() -> None:
    with pytest.raises(Exception):  # noqa: B017 - pydantic ValidationError
        OptimizationInput(
            symbols=("A", "B"),
            expected_returns=(Decimal("0.05"),),
            covariance_matrix=(
                (Decimal("0.04"), Decimal("0")),
                (Decimal("0"), Decimal("0.01")),
            ),
        )


def test_mismatched_covariance_shape_rejected() -> None:
    with pytest.raises(Exception):  # noqa: B017 - pydantic ValidationError
        OptimizationInput(
            symbols=("A", "B"),
            expected_returns=(Decimal("0.05"), Decimal("0.03")),
            covariance_matrix=((Decimal("0.04"), Decimal("0")),),
        )
