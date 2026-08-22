"""The ``Money`` value object.

All monetary values in FinApp use :class:`decimal.Decimal`, never ``float``,
to avoid binary floating-point rounding errors in financial calculations.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator

from finapp.domain.exceptions import CurrencyMismatchError
from finapp.domain.value_objects.enums import Currency


class Money(BaseModel):
    """An immutable amount of money in a specific currency.

    Arithmetic operators enforce currency consistency: adding or subtracting
    :class:`Money` in different currencies raises :class:`CurrencyMismatchError`
    rather than silently producing a nonsensical result. FinApp does not
    perform currency conversion inside the domain layer; that is an
    application/infrastructure concern (e.g. an FX-rate provider) left for a
    later sprint.
    """

    model_config = ConfigDict(frozen=True)

    amount: Decimal
    currency: Currency

    @field_validator("amount")
    @classmethod
    def _amount_must_be_finite(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("Money.amount must be a finite Decimal")
        return value

    @classmethod
    def zero(cls, currency: Currency) -> "Money":
        """Return a zero-value :class:`Money` in the given currency."""

        return cls(amount=Decimal("0"), currency=currency)

    def _require_same_currency(self, other: "Money") -> None:
        if self.currency != other.currency:
            raise CurrencyMismatchError(expected=self.currency.value, actual=other.currency.value)

    def __add__(self, other: "Money") -> "Money":
        self._require_same_currency(other)
        return Money(amount=self.amount + other.amount, currency=self.currency)

    def __sub__(self, other: "Money") -> "Money":
        self._require_same_currency(other)
        return Money(amount=self.amount - other.amount, currency=self.currency)

    def __neg__(self) -> "Money":
        return Money(amount=-self.amount, currency=self.currency)

    def __mul__(self, factor: Decimal | int) -> "Money":
        return Money(amount=self.amount * Decimal(factor), currency=self.currency)

    __rmul__ = __mul__

    def __lt__(self, other: "Money") -> bool:
        self._require_same_currency(other)
        return self.amount < other.amount

    def __le__(self, other: "Money") -> bool:
        self._require_same_currency(other)
        return self.amount <= other.amount

    def __gt__(self, other: "Money") -> bool:
        self._require_same_currency(other)
        return self.amount > other.amount

    def __ge__(self, other: "Money") -> bool:
        self._require_same_currency(other)
        return self.amount >= other.amount

    def is_zero(self) -> bool:
        return self.amount == Decimal("0")

    def is_negative(self) -> bool:
        return self.amount < Decimal("0")

    def __str__(self) -> str:
        return f"{self.amount} {self.currency.value}"
