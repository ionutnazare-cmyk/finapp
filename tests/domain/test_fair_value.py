from __future__ import annotations

from decimal import Decimal

import pytest

from finapp.domain.exceptions import CurrencyMismatchError, FairValueModelError
from finapp.domain.services.fair_value import FairValueEstimate, FairValueEstimator
from finapp.domain.value_objects.enums import Currency
from finapp.domain.value_objects.money import Money


def test_gordon_growth_ddm_exact_value() -> None:
    # D1=3.00, r=0.10, g=0.04 -> 3.00 / 0.06 = 50.00
    estimate = FairValueEstimator().gordon_growth_dividend_discount(
        symbol="TLV",
        next_annual_dividend_per_share=Money(amount=Decimal("3.00"), currency=Currency.RON),
        required_return=Decimal("0.10"),
        dividend_growth_rate=Decimal("0.04"),
    )
    assert estimate.fair_value_per_share == Money(amount=Decimal("50.00"), currency=Currency.RON)
    assert estimate.model == "gordon_growth_ddm"


def test_gordon_growth_ddm_margin_of_safety() -> None:
    estimate = FairValueEstimator().gordon_growth_dividend_discount(
        symbol="TLV",
        next_annual_dividend_per_share=Money(amount=Decimal("3.00"), currency=Currency.RON),
        required_return=Decimal("0.10"),
        dividend_growth_rate=Decimal("0.04"),
        current_price=Money(amount=Decimal("40.00"), currency=Currency.RON),
    )
    # (50 - 40) / 40 = 0.25
    assert estimate.margin_of_safety == Decimal("0.25")


def test_gordon_growth_ddm_requires_return_above_growth() -> None:
    with pytest.raises(FairValueModelError):
        FairValueEstimator().gordon_growth_dividend_discount(
            symbol="TLV",
            next_annual_dividend_per_share=Money(amount=Decimal("3.00"), currency=Currency.RON),
            required_return=Decimal("0.05"),
            dividend_growth_rate=Decimal("0.05"),
        )


def test_dividend_yield_target_exact_value() -> None:
    # 2.50 / 0.05 = 50.00
    estimate = FairValueEstimator().dividend_yield_target(
        symbol="SNP",
        annual_dividend_per_share=Money(amount=Decimal("2.50"), currency=Currency.RON),
        target_yield=Decimal("0.05"),
    )
    assert estimate.fair_value_per_share == Money(amount=Decimal("50.00"), currency=Currency.RON)


def test_dividend_yield_target_requires_positive_yield() -> None:
    with pytest.raises(FairValueModelError):
        FairValueEstimator().dividend_yield_target(
            symbol="SNP",
            annual_dividend_per_share=Money(amount=Decimal("2.50"), currency=Currency.RON),
            target_yield=Decimal("0"),
        )


def test_price_to_earnings_relative_exact_value() -> None:
    # 4.00 * 15 = 60.00
    estimate = FairValueEstimator().price_to_earnings_relative(
        symbol="H2O",
        earnings_per_share=Money(amount=Decimal("4.00"), currency=Currency.RON),
        target_price_to_earnings=Decimal("15"),
    )
    assert estimate.fair_value_per_share == Money(amount=Decimal("60.00"), currency=Currency.RON)


def test_price_to_earnings_relative_requires_positive_earnings() -> None:
    with pytest.raises(FairValueModelError):
        FairValueEstimator().price_to_earnings_relative(
            symbol="H2O",
            earnings_per_share=Money(amount=Decimal("-1.00"), currency=Currency.RON),
            target_price_to_earnings=Decimal("15"),
        )


def test_price_to_earnings_relative_requires_positive_multiple() -> None:
    with pytest.raises(FairValueModelError):
        FairValueEstimator().price_to_earnings_relative(
            symbol="H2O",
            earnings_per_share=Money(amount=Decimal("4.00"), currency=Currency.RON),
            target_price_to_earnings=Decimal("0"),
        )


def test_margin_of_safety_none_without_current_price() -> None:
    estimate = FairValueEstimator().dividend_yield_target(
        symbol="SNP",
        annual_dividend_per_share=Money(amount=Decimal("2.50"), currency=Currency.RON),
        target_yield=Decimal("0.05"),
    )
    assert estimate.margin_of_safety is None


def test_margin_of_safety_none_when_current_price_is_zero() -> None:
    estimate = FairValueEstimate(
        symbol="SNP",
        model="test",
        fair_value_per_share=Money(amount=Decimal("50"), currency=Currency.RON),
        current_price=Money(amount=Decimal("0"), currency=Currency.RON),
    )
    assert estimate.margin_of_safety is None


def test_currency_mismatch_between_fair_value_and_current_price_rejected() -> None:
    with pytest.raises(CurrencyMismatchError):
        FairValueEstimate(
            symbol="SNP",
            model="test",
            fair_value_per_share=Money(amount=Decimal("50"), currency=Currency.RON),
            current_price=Money(amount=Decimal("10"), currency=Currency.USD),
        )
