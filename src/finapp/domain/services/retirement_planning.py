"""Retirement planning: simulates an accumulation phase (regular
contributions) followed by a retirement/decumulation phase (regular
withdrawals), and reports the probability that the portfolio is fully
depleted before the retirement horizon ends.

This is a materially different picture than accumulation-only projections
(see ``finapp.domain.services.monte_carlo``): it's the difference between
"how big might my portfolio get" and "will my money actually last through
retirement." Built the same way — a domain service, no I/O, using NumPy for
vectorized random sampling — but modeling two phases with independent
return/volatility assumptions and a switch from contributions to
withdrawals.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator

from finapp.domain.value_objects.money import Money


class RetirementPlanAssumptions(BaseModel):
    """Assumptions for a two-phase retirement simulation.

    ``accumulation_years`` may be zero (already retired: skip straight to
    the withdrawal phase from the starting value). ``retirement_years``
    must be positive — a plan with no retirement phase isn't a retirement
    plan. All returns/volatilities are annual figures expressed as decimals
    (e.g. ``Decimal("0.07")`` for 7%); ``annual_contribution`` is added at
    the start of each accumulation year, ``annual_withdrawal`` is taken at
    the start of each retirement year, both before that year's return is
    applied.
    """

    model_config = ConfigDict(frozen=True)

    accumulation_years: int = Field(ge=0, le=80)
    accumulation_expected_return: Decimal
    accumulation_volatility: Decimal
    annual_contribution: Decimal = Decimal("0")

    retirement_years: int = Field(gt=0, le=80)
    retirement_expected_return: Decimal
    retirement_volatility: Decimal
    annual_withdrawal: Decimal

    simulations: int = Field(gt=0, le=200_000)
    random_seed: int | None = None

    @field_validator("accumulation_volatility", "retirement_volatility")
    @classmethod
    def _volatility_non_negative(cls, value: Decimal) -> Decimal:
        if value < Decimal("0"):
            raise ValueError(f"volatility cannot be negative, got {value}")
        return value

    @field_validator("annual_contribution", "annual_withdrawal")
    @classmethod
    def _amount_non_negative(cls, value: Decimal) -> Decimal:
        if value < Decimal("0"):
            raise ValueError(f"amount cannot be negative, got {value}")
        return value


@dataclass(frozen=True)
class RetirementPlanResult:
    """Summary statistics from a two-phase retirement simulation."""

    starting_value: Money
    value_at_retirement_percentile_10: Money
    value_at_retirement_percentile_50: Money
    value_at_retirement_percentile_90: Money
    value_at_end_percentile_10: Money
    value_at_end_percentile_50: Money
    value_at_end_percentile_90: Money
    probability_of_depletion: Decimal


class RetirementPlanner:
    """Simulates an accumulation phase followed by a retirement
    (decumulation) phase, starting from a single portfolio value.

    A path is counted as "depleted" the first time its value hits zero
    during the retirement phase; once depleted, a path stays at zero for
    the remainder of the simulation (it can't earn returns on money it no
    longer has, and a bad year can't be "undone" by a later good one).
    """

    def plan(self, starting_value: Money, assumptions: RetirementPlanAssumptions) -> RetirementPlanResult:
        rng = np.random.default_rng(assumptions.random_seed)
        n = assumptions.simulations
        currency = starting_value.currency

        values = np.full(n, float(starting_value.amount), dtype=float)

        accumulation_returns = rng.normal(
            loc=float(assumptions.accumulation_expected_return),
            scale=float(assumptions.accumulation_volatility),
            size=(n, assumptions.accumulation_years),
        )
        contribution = float(assumptions.annual_contribution)
        for year in range(assumptions.accumulation_years):
            values = (values + contribution) * (1.0 + accumulation_returns[:, year])
            values = np.maximum(values, 0.0)

        value_at_retirement = values.copy()

        retirement_returns = rng.normal(
            loc=float(assumptions.retirement_expected_return),
            scale=float(assumptions.retirement_volatility),
            size=(n, assumptions.retirement_years),
        )
        withdrawal = float(assumptions.annual_withdrawal)
        depleted = np.zeros(n, dtype=bool)
        for year in range(assumptions.retirement_years):
            # Withdraw first and floor at zero *before* applying the year's
            # return, so a depleted path can't spuriously "recover" via a
            # negative balance times a negative return.
            values = np.maximum(values - withdrawal, 0.0)
            depleted = depleted | (values <= 0.0)
            values = np.maximum(values * (1.0 + retirement_returns[:, year]), 0.0)

        probability_of_depletion = float(np.mean(depleted))

        def money(amount: float) -> Money:
            return Money(amount=Decimal(str(round(amount, 2))), currency=currency)

        p10_ret, p50_ret, p90_ret = np.percentile(value_at_retirement, [10, 50, 90])
        p10_end, p50_end, p90_end = np.percentile(values, [10, 50, 90])

        return RetirementPlanResult(
            starting_value=starting_value,
            value_at_retirement_percentile_10=money(float(p10_ret)),
            value_at_retirement_percentile_50=money(float(p50_ret)),
            value_at_retirement_percentile_90=money(float(p90_ret)),
            value_at_end_percentile_10=money(float(p10_end)),
            value_at_end_percentile_50=money(float(p50_end)),
            value_at_end_percentile_90=money(float(p90_end)),
            probability_of_depletion=Decimal(str(round(probability_of_depletion, 4))),
        )
