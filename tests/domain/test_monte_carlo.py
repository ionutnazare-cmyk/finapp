from __future__ import annotations

from decimal import Decimal

import pytest

from finapp.domain.services.monte_carlo import (
    MonteCarloAssumptions,
    MonteCarloSimulator,
)
from finapp.domain.value_objects.enums import Currency
from finapp.domain.value_objects.money import Money


def test_zero_volatility_zero_contribution_is_a_pure_compounding_identity() -> None:
    starting = Money(amount=Decimal("1000"), currency=Currency.RON)
    assumptions = MonteCarloAssumptions(
        expected_annual_return=Decimal("0"),
        annual_volatility=Decimal("0"),
        years=5,
        simulations=10,
    )
    result = MonteCarloSimulator().simulate(starting, assumptions)

    assert result.percentile_10 == starting
    assert result.percentile_50 == starting
    assert result.percentile_90 == starting
    assert result.mean == starting
    assert result.minimum == starting
    assert result.maximum == starting
    assert result.probability_of_loss == Decimal("0")


def test_deterministic_growth_with_contribution_and_zero_volatility() -> None:
    starting = Money(amount=Decimal("1000"), currency=Currency.RON)
    assumptions = MonteCarloAssumptions(
        expected_annual_return=Decimal("0.05"),
        annual_volatility=Decimal("0"),
        years=2,
        simulations=10,
        annual_contribution=Decimal("100"),
    )
    result = MonteCarloSimulator().simulate(starting, assumptions)

    # Year 1: (1000 + 100) * 1.05 = 1155
    # Year 2: (1155 + 100) * 1.05 = 1317.75
    expected = Money(amount=Decimal("1317.75"), currency=Currency.RON)
    assert result.percentile_50 == expected
    assert result.mean == expected
    assert result.minimum == expected
    assert result.maximum == expected
    assert result.probability_of_loss == Decimal("0")


def test_value_is_floored_at_zero() -> None:
    starting = Money(amount=Decimal("1000"), currency=Currency.RON)
    assumptions = MonteCarloAssumptions(
        expected_annual_return=Decimal("-1.5"),
        annual_volatility=Decimal("0"),
        years=1,
        simulations=5,
    )
    result = MonteCarloSimulator().simulate(starting, assumptions)

    assert result.minimum == Money(amount=Decimal("0"), currency=Currency.RON)
    assert result.maximum == Money(amount=Decimal("0"), currency=Currency.RON)
    assert result.probability_of_loss == Decimal("1")


def test_same_seed_is_reproducible() -> None:
    starting = Money(amount=Decimal("10000"), currency=Currency.RON)
    assumptions = MonteCarloAssumptions(
        expected_annual_return=Decimal("0.06"),
        annual_volatility=Decimal("0.15"),
        years=10,
        simulations=1000,
        random_seed=42,
    )
    simulator = MonteCarloSimulator()
    first = simulator.simulate(starting, assumptions)
    second = simulator.simulate(starting, assumptions)

    assert first == second


def test_different_seeds_can_differ() -> None:
    starting = Money(amount=Decimal("10000"), currency=Currency.RON)
    simulator = MonteCarloSimulator()
    result_a = simulator.simulate(
        starting,
        MonteCarloAssumptions(
            expected_annual_return=Decimal("0.06"),
            annual_volatility=Decimal("0.20"),
            years=10,
            simulations=1000,
            random_seed=1,
        ),
    )
    result_b = simulator.simulate(
        starting,
        MonteCarloAssumptions(
            expected_annual_return=Decimal("0.06"),
            annual_volatility=Decimal("0.20"),
            years=10,
            simulations=1000,
            random_seed=2,
        ),
    )
    assert result_a != result_b


def test_probability_of_loss_is_between_zero_and_one() -> None:
    starting = Money(amount=Decimal("10000"), currency=Currency.RON)
    assumptions = MonteCarloAssumptions(
        expected_annual_return=Decimal("0.05"),
        annual_volatility=Decimal("0.18"),
        years=20,
        simulations=2000,
        random_seed=7,
    )
    result = MonteCarloSimulator().simulate(starting, assumptions)
    assert Decimal("0") <= result.probability_of_loss <= Decimal("1")


def test_negative_volatility_rejected() -> None:
    with pytest.raises(Exception):  # noqa: B017 - pydantic ValidationError
        MonteCarloAssumptions(
            expected_annual_return=Decimal("0.05"),
            annual_volatility=Decimal("-0.1"),
            years=10,
            simulations=100,
        )


def test_negative_contribution_rejected() -> None:
    with pytest.raises(Exception):  # noqa: B017 - pydantic ValidationError
        MonteCarloAssumptions(
            expected_annual_return=Decimal("0.05"),
            annual_volatility=Decimal("0.1"),
            years=10,
            simulations=100,
            annual_contribution=Decimal("-50"),
        )


def test_non_positive_years_rejected() -> None:
    with pytest.raises(Exception):  # noqa: B017 - pydantic ValidationError
        MonteCarloAssumptions(
            expected_annual_return=Decimal("0.05"),
            annual_volatility=Decimal("0.1"),
            years=0,
            simulations=100,
        )


def test_excessive_simulations_rejected() -> None:
    with pytest.raises(Exception):  # noqa: B017 - pydantic ValidationError
        MonteCarloAssumptions(
            expected_annual_return=Decimal("0.05"),
            annual_volatility=Decimal("0.1"),
            years=10,
            simulations=1_000_000,
        )
