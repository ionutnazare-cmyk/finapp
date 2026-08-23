"""Mean-variance (Markowitz) portfolio optimization.

A domain service, like ``monte_carlo``: pure quantitative logic with no I/O,
using SciPy's constrained optimizer to find portfolio weights. Long-only
(no shorting) and fully-invested (weights sum to 1) throughout — this
sprint doesn't model leverage, shorting, or per-asset position limits
beyond the [0, 1] bound.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

import numpy as np
from pydantic import BaseModel, ConfigDict, model_validator
from scipy.optimize import minimize

from finapp.domain.exceptions import OptimizationFailedError


class OptimizationInput(BaseModel):
    """Inputs to a mean-variance optimization: one expected annual return per
    instrument symbol, and their covariance matrix of annual returns.

    ``covariance_matrix`` must be an N×N matrix (N = number of symbols)
    whose row/column order matches ``symbols``. Basic shape consistency is
    checked here; full positive-semi-definiteness is left for the optimizer
    to fail on via :class:`~finapp.domain.exceptions.OptimizationFailedError`
    rather than duplicating that check here.
    """

    model_config = ConfigDict(frozen=True)

    symbols: tuple[str, ...]
    expected_returns: tuple[Decimal, ...]
    covariance_matrix: tuple[tuple[Decimal, ...], ...]
    risk_free_rate: Decimal = Decimal("0")

    @model_validator(mode="after")
    def _shapes_must_be_consistent(self) -> "OptimizationInput":
        n = len(self.symbols)
        if n < 2:
            raise ValueError("At least 2 instruments are required to optimize a portfolio")
        if len(self.expected_returns) != n:
            raise ValueError("expected_returns must have exactly one entry per symbol")
        if len(self.covariance_matrix) != n or any(len(row) != n for row in self.covariance_matrix):
            raise ValueError(
                f"covariance_matrix must be {n}x{n} to match {n} symbols"
            )
        return self


@dataclass(frozen=True)
class OptimizedAllocation:
    """One instrument's weight in an optimized portfolio."""

    symbol: str
    weight: Decimal


@dataclass(frozen=True)
class OptimizationResult:
    """The outcome of a mean-variance optimization."""

    allocations: tuple[OptimizedAllocation, ...]
    expected_return: Decimal
    expected_volatility: Decimal
    sharpe_ratio: Decimal


class PortfolioOptimizer:
    """Finds long-only, fully-invested portfolio weights using SciPy's SLSQP
    constrained optimizer.
    """

    def maximize_sharpe_ratio(self, inputs: OptimizationInput) -> OptimizationResult:
        """Find the weights that maximize (return − risk_free_rate) / volatility."""

        expected_returns, covariance = self._to_numpy(inputs)
        risk_free_rate = float(inputs.risk_free_rate)

        def negative_sharpe(weights: np.ndarray) -> float:
            portfolio_return = float(np.dot(weights, expected_returns))
            portfolio_volatility = float(np.sqrt(weights @ covariance @ weights))
            if portfolio_volatility == 0.0:
                return 0.0 if portfolio_return <= risk_free_rate else -1e6
            return -(portfolio_return - risk_free_rate) / portfolio_volatility

        weights = self._minimize(negative_sharpe, len(inputs.symbols), extra_constraints=())
        return self._build_result(inputs, weights, expected_returns, covariance, risk_free_rate)

    def minimize_volatility(
        self, inputs: OptimizationInput, target_return: Decimal | None = None
    ) -> OptimizationResult:
        """Find the lowest-volatility weights, optionally constrained to a
        specific target expected return. With no target, this finds the
        global minimum-variance portfolio.
        """

        expected_returns, covariance = self._to_numpy(inputs)

        def variance(weights: np.ndarray) -> float:
            return float(weights @ covariance @ weights)

        extra_constraints: tuple[dict[str, object], ...] = ()
        if target_return is not None:
            target = float(target_return)
            extra_constraints = (
                {
                    "type": "eq",
                    "fun": lambda w: float(np.dot(w, expected_returns)) - target,
                },
            )

        weights = self._minimize(variance, len(inputs.symbols), extra_constraints)
        return self._build_result(
            inputs, weights, expected_returns, covariance, float(inputs.risk_free_rate)
        )

    @staticmethod
    def _to_numpy(inputs: OptimizationInput) -> tuple[np.ndarray, np.ndarray]:
        expected_returns = np.array([float(r) for r in inputs.expected_returns])
        covariance = np.array([[float(c) for c in row] for row in inputs.covariance_matrix])
        return expected_returns, covariance

    @staticmethod
    def _minimize(
        objective: Callable[[np.ndarray], float],
        n: int,
        extra_constraints: tuple[dict[str, object], ...],
    ) -> np.ndarray:
        constraints: list[dict[str, object]] = [
            {"type": "eq", "fun": lambda w: float(np.sum(w)) - 1.0}
        ]
        constraints.extend(extra_constraints)
        bounds = tuple((0.0, 1.0) for _ in range(n))
        initial_guess = np.full(n, 1.0 / n)

        result = minimize(
            objective,
            initial_guess,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )
        if not result.success:
            raise OptimizationFailedError(str(result.message))

        weights = np.clip(result.x, 0.0, 1.0)
        total = weights.sum()
        if total == 0.0:
            raise OptimizationFailedError("optimizer returned an all-zero weight vector")
        return weights / total

    @staticmethod
    def _build_result(
        inputs: OptimizationInput,
        weights: np.ndarray,
        expected_returns: np.ndarray,
        covariance: np.ndarray,
        risk_free_rate: float,
    ) -> OptimizationResult:
        portfolio_return = float(np.dot(weights, expected_returns))
        portfolio_volatility = float(np.sqrt(weights @ covariance @ weights))
        sharpe = (
            (portfolio_return - risk_free_rate) / portfolio_volatility
            if portfolio_volatility > 0.0
            else 0.0
        )

        allocations = tuple(
            OptimizedAllocation(symbol=symbol, weight=Decimal(str(round(float(weight), 6))))
            for symbol, weight in zip(inputs.symbols, weights, strict=True)
        )

        return OptimizationResult(
            allocations=allocations,
            expected_return=Decimal(str(round(portfolio_return, 6))),
            expected_volatility=Decimal(str(round(portfolio_volatility, 6))),
            sharpe_ratio=Decimal(str(round(sharpe, 6))),
        )
