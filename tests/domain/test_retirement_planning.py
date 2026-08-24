from __future__ import annotations

from decimal import Decimal

import pytest

from finapp.domain.services.retirement_planning import (
    RetirementPlanAssumptions,
    RetirementPlanner,
)
from finapp.domain.value_objects.enums import Currency
from finapp.domain.value_objects.money import Money


def test_deterministic_accumulation_then_withdrawal_no_depletion() -> None:
    starting = Money(amount=Decimal("1000"), currency=Currency.RON)
    assumptions = RetirementPlanAssumptions(
        accumulation_years=2,
        accumulation_expected_return=Decimal("0.05"),
        accumulation_volatility=Decimal("0"),
        annual_contribution=Decimal("100"),
        retirement_years=2,
        retirement_expected_return=Decimal("0"),
        retirement_volatility=Decimal("0"),
        annual_withdrawal=Decimal("500"),
        simulations=10,
    )
    result = RetirementPlanner().plan(starting, assumptions)

    # Accumulation: (1000+100)*1.05=1155, (1155+100)*1.05=1317.75
    retirement_value = Money(amount=Decimal("1317.75"), currency=Currency.RON)
    assert result.value_at_retirement_percentile_50 == retirement_value

    # Withdrawal: 1317.75-500=817.75, 817.75-500=317.75 (0% growth)
    end_value = Money(amount=Decimal("317.75"), currency=Currency.RON)
    assert result.value_at_end_percentile_50 == end_value
    assert result.probability_of_depletion == Decimal("0")


def test_deterministic_depletion_during_retirement() -> None:
    starting = Money(amount=Decimal("1000"), currency=Currency.RON)
    assumptions = RetirementPlanAssumptions(
        accumulation_years=1,
        accumulation_expected_return=Decimal("0"),
        accumulation_volatility=Decimal("0"),
        annual_contribution=Decimal("0"),
        retirement_years=3,
        retirement_expected_return=Decimal("0"),
        retirement_volatility=Decimal("0"),
        annual_withdrawal=Decimal("400"),
        simulations=10,
    )
    result = RetirementPlanner().plan(starting, assumptions)

    # 1000 -400=600 -400=200 -400=-200 -> depleted, floored at 0
    assert result.value_at_end_percentile_50 == Money(amount=Decimal("0"), currency=Currency.RON)
    assert result.probability_of_depletion == Decimal("1")


def test_zero_accumulation_years_skips_straight_to_retirement() -> None:
    starting = Money(amount=Decimal("1000"), currency=Currency.RON)
    assumptions = RetirementPlanAssumptions(
        accumulation_years=0,
        accumulation_expected_return=Decimal("0.08"),
        accumulation_volatility=Decimal("0"),
        retirement_years=1,
        retirement_expected_return=Decimal("0.10"),
        retirement_volatility=Decimal("0"),
        annual_withdrawal=Decimal("200"),
        simulations=10,
    )
    result = RetirementPlanner().plan(starting, assumptions)

    assert result.value_at_retirement_percentile_50 == starting
    # (1000 - 200) * 1.10 = 880
    assert result.value_at_end_percentile_50 == Money(amount=Decimal("880"), currency=Currency.RON)
    assert result.probability_of_depletion == Decimal("0")


def test_same_seed_is_reproducible() -> None:
    starting = Money(amount=Decimal("100000"), currency=Currency.RON)
    assumptions = RetirementPlanAssumptions(
        accumulation_years=15,
        accumulation_expected_return=Decimal("0.07"),
        accumulation_volatility=Decimal("0.15"),
        annual_contribution=Decimal("5000"),
        retirement_years=25,
        retirement_expected_return=Decimal("0.04"),
        retirement_volatility=Decimal("0.08"),
        annual_withdrawal=Decimal("40000"),
        simulations=2000,
        random_seed=123,
    )
    planner = RetirementPlanner()
    first = planner.plan(starting, assumptions)
    second = planner.plan(starting, assumptions)
    assert first == second


def test_probability_of_depletion_is_between_zero_and_one() -> None:
    starting = Money(amount=Decimal("100000"), currency=Currency.RON)
    assumptions = RetirementPlanAssumptions(
        accumulation_years=10,
        accumulation_expected_return=Decimal("0.06"),
        accumulation_volatility=Decimal("0.16"),
        annual_contribution=Decimal("3000"),
        retirement_years=30,
        retirement_expected_return=Decimal("0.03"),
        retirement_volatility=Decimal("0.10"),
        annual_withdrawal=Decimal("30000"),
        simulations=2000,
        random_seed=7,
    )
    result = RetirementPlanner().plan(starting, assumptions)
    assert Decimal("0") <= result.probability_of_depletion <= Decimal("1")


def test_negative_volatility_rejected() -> None:
    with pytest.raises(Exception):  # noqa: B017 - pydantic ValidationError
        RetirementPlanAssumptions(
            accumulation_years=5,
            accumulation_expected_return=Decimal("0.05"),
            accumulation_volatility=Decimal("-0.1"),
            retirement_years=20,
            retirement_expected_return=Decimal("0.03"),
            retirement_volatility=Decimal("0.05"),
            annual_withdrawal=Decimal("10000"),
            simulations=100,
        )


def test_negative_withdrawal_rejected() -> None:
    with pytest.raises(Exception):  # noqa: B017 - pydantic ValidationError
        RetirementPlanAssumptions(
            accumulation_years=5,
            accumulation_expected_return=Decimal("0.05"),
            accumulation_volatility=Decimal("0.1"),
            retirement_years=20,
            retirement_expected_return=Decimal("0.03"),
            retirement_volatility=Decimal("0.05"),
            annual_withdrawal=Decimal("-10000"),
            simulations=100,
        )


def test_zero_retirement_years_rejected() -> None:
    with pytest.raises(Exception):  # noqa: B017 - pydantic ValidationError
        RetirementPlanAssumptions(
            accumulation_years=5,
            accumulation_expected_return=Decimal("0.05"),
            accumulation_volatility=Decimal("0.1"),
            retirement_years=0,
            retirement_expected_return=Decimal("0.03"),
            retirement_volatility=Decimal("0.05"),
            annual_withdrawal=Decimal("10000"),
            simulations=100,
        )
