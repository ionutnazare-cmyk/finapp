"""Monte Carlo simulation of a portfolio's future value.

This is a domain *service* rather than an entity or value object: it's
stateless logic that doesn't naturally belong to a single ``Portfolio`` or
``Position``. It lives in the domain layer (not application) because it has
no I/O and no dependency on any port — it's pure business/quantitative
logic operating on plain numbers, same as ``Position.market_value`` or
``Portfolio.total_book_cost``. NumPy is used for vectorized random sampling;
unlike pandas/streamlit/requests/openpyxl, it's a numerical library, not an
I/O one, so it doesn't cross the boundary the architecture doc warns about.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator

from finapp.domain.value_objects.money import Money


class MonteCarloAssumptions(BaseModel):
    """Assumptions driving a Monte Carlo simulation.

    ``expected_annual_return`` and ``annual_volatility`` are annual figures
    expressed as decimals (e.g. ``Decimal("0.07")`` for 7%). Each simulated
    year draws an independent normally-distributed annual return with this
    mean and standard deviation; ``annual_contribution`` (if any) is added
    to the portfolio at the *start* of each year, before that year's return
    is applied. ``simulations`` and ``years`` are capped to keep a single
    run's memory and runtime bounded on an ordinary desktop.
    """

    model_config = ConfigDict(frozen=True)

    expected_annual_return: Decimal
    annual_volatility: Decimal
    years: int = Field(gt=0, le=100)
    simulations: int = Field(gt=0, le=200_000)
    annual_contribution: Decimal = Decimal("0")
    random_seed: int | None = None

    @field_validator("annual_volatility")
    @classmethod
    def _volatility_non_negative(cls, value: Decimal) -> Decimal:
        if value < Decimal("0"):
            raise ValueError(f"annual_volatility cannot be negative, got {value}")
        return value

    @field_validator("annual_contribution")
    @classmethod
    def _contribution_non_negative(cls, value: Decimal) -> Decimal:
        if value < Decimal("0"):
            raise ValueError(f"annual_contribution cannot be negative, got {value}")
        return value


@dataclass(frozen=True)
class MonteCarloResult:
    """Summary statistics of simulated ending portfolio values across all paths."""

    starting_value: Money
    percentile_10: Money
    percentile_50: Money
    percentile_90: Money
    mean: Money
    minimum: Money
    maximum: Money
    probability_of_loss: Decimal


class MonteCarloSimulator:
    """Simulates portfolio value paths using independent annual normal returns
    compounded year over year (a simplified geometric-return model — not a
    continuous-time geometric Brownian motion, and returns are treated as
    independent across years, with no correlation or fat tails modeled).

    A portfolio's value is floored at zero each year: it can't go negative,
    even if a drawn return would otherwise imply a negative balance.
    """

    def simulate(self, starting_value: Money, assumptions: MonteCarloAssumptions) -> MonteCarloResult:
        rng = np.random.default_rng(assumptions.random_seed)

        mean = float(assumptions.expected_annual_return)
        volatility = float(assumptions.annual_volatility)
        contribution = float(assumptions.annual_contribution)
        start = float(starting_value.amount)

        annual_returns = rng.normal(
            loc=mean, scale=volatility, size=(assumptions.simulations, assumptions.years)
        )

        values = np.full(assumptions.simulations, start, dtype=float)
        for year in range(assumptions.years):
            values = (values + contribution) * (1.0 + annual_returns[:, year])
            values = np.maximum(values, 0.0)

        percentile_10, percentile_50, percentile_90 = np.percentile(values, [10, 50, 90])
        probability_of_loss = float(np.mean(values < start))
        currency = starting_value.currency

        def money(amount: float) -> Money:
            return Money(amount=Decimal(str(round(amount, 2))), currency=currency)

        return MonteCarloResult(
            starting_value=starting_value,
            percentile_10=money(float(percentile_10)),
            percentile_50=money(float(percentile_50)),
            percentile_90=money(float(percentile_90)),
            mean=money(float(np.mean(values))),
            minimum=money(float(np.min(values))),
            maximum=money(float(np.max(values))),
            probability_of_loss=Decimal(str(round(probability_of_loss, 4))),
        )
