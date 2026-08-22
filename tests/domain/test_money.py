from __future__ import annotations

from decimal import Decimal

import pytest

from finapp.domain.exceptions import CurrencyMismatchError
from finapp.domain.value_objects.enums import Currency
from finapp.domain.value_objects.money import Money


def test_zero_constructs_zero_amount() -> None:
    money = Money.zero(Currency.RON)
    assert money.amount == Decimal("0")
    assert money.is_zero()


def test_addition_same_currency() -> None:
    a = Money(amount=Decimal("10.50"), currency=Currency.RON)
    b = Money(amount=Decimal("4.25"), currency=Currency.RON)
    assert a + b == Money(amount=Decimal("14.75"), currency=Currency.RON)


def test_addition_different_currency_raises() -> None:
    a = Money(amount=Decimal("10"), currency=Currency.RON)
    b = Money(amount=Decimal("10"), currency=Currency.USD)
    with pytest.raises(CurrencyMismatchError):
        _ = a + b


def test_subtraction_and_negative_amount() -> None:
    a = Money(amount=Decimal("5"), currency=Currency.RON)
    b = Money(amount=Decimal("8"), currency=Currency.RON)
    result = a - b
    assert result.amount == Decimal("-3")
    assert result.is_negative()


def test_multiplication_by_scalar() -> None:
    price = Money(amount=Decimal("12.5"), currency=Currency.RON)
    total = price * Decimal("3")
    assert total.amount == Decimal("37.5")
    assert total.currency == Currency.RON


def test_ordering_requires_same_currency() -> None:
    a = Money(amount=Decimal("5"), currency=Currency.RON)
    b = Money(amount=Decimal("10"), currency=Currency.RON)
    assert a < b
    assert b > a
    with pytest.raises(CurrencyMismatchError):
        _ = a < Money(amount=Decimal("5"), currency=Currency.USD)


def test_money_is_immutable() -> None:
    money = Money(amount=Decimal("1"), currency=Currency.RON)
    with pytest.raises(Exception):  # noqa: B017 - pydantic ValidationError subclass
        money.amount = Decimal("2")  # type: ignore[misc]


def test_non_finite_amount_rejected() -> None:
    with pytest.raises(Exception):  # noqa: B017 - pydantic ValidationError
        Money(amount=Decimal("NaN"), currency=Currency.RON)
