"""The ``Position`` entity: a holding of one instrument within a portfolio."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from finapp.domain.entities.instrument import Instrument
from finapp.domain.exceptions import (
    CurrencyMismatchError,
    InsufficientSharesError,
    InvalidQuantityError,
)
from finapp.domain.value_objects.money import Money


class Position(BaseModel):
    """An immutable snapshot of holding some quantity of an :class:`Instrument`
    at a given average cost per share.

    ``Position`` is immutable: every change (buying more shares, selling
    shares) returns a *new* ``Position`` rather than mutating the existing
    one. This keeps the domain model easy to reason about and test, and
    lets :class:`~finapp.domain.entities.portfolio.Portfolio` remain the
    single place that decides what happens to the previous snapshot.
    """

    model_config = ConfigDict(frozen=True)

    instrument: Instrument
    quantity: Decimal
    average_cost: Money  # cost per single share/unit, in instrument.currency

    @field_validator("quantity")
    @classmethod
    def _quantity_not_negative(cls, value: Decimal) -> Decimal:
        if value < Decimal("0"):
            raise InvalidQuantityError(f"Position.quantity cannot be negative, got {value}")
        return value

    @model_validator(mode="after")
    def _average_cost_matches_instrument_currency(self) -> "Position":
        if self.average_cost.currency != self.instrument.currency:
            raise CurrencyMismatchError(
                expected=self.instrument.currency.value,
                actual=self.average_cost.currency.value,
            )
        return self

    def book_cost(self) -> Money:
        """Total amount paid for the currently held shares (quantity × average cost)."""

        return self.average_cost * self.quantity

    def market_value(self, price: Money) -> Money:
        """Current market value of the position at the given per-share ``price``."""

        if price.currency != self.instrument.currency:
            raise CurrencyMismatchError(
                expected=self.instrument.currency.value, actual=price.currency.value
            )
        return price * self.quantity

    def unrealized_pnl(self, price: Money) -> Money:
        """Unrealized profit/loss versus book cost at the given per-share ``price``."""

        return self.market_value(price) - self.book_cost()

    def with_additional_shares(self, quantity: Decimal, price: Money) -> "Position":
        """Return a new ``Position`` reflecting a purchase of ``quantity`` more
        shares at ``price`` per share, recomputing the weighted-average cost."""

        if quantity <= Decimal("0"):
            raise InvalidQuantityError(
                f"Cannot add a non-positive quantity of shares, got {quantity}"
            )
        if price.currency != self.instrument.currency:
            raise CurrencyMismatchError(
                expected=self.instrument.currency.value, actual=price.currency.value
            )

        new_quantity = self.quantity + quantity
        new_total_cost = self.book_cost() + (price * quantity)
        new_average_cost = Money(
            amount=new_total_cost.amount / new_quantity,
            currency=self.instrument.currency,
        )
        return Position(
            instrument=self.instrument,
            quantity=new_quantity,
            average_cost=new_average_cost,
        )

    def with_reduced_shares(self, quantity: Decimal) -> "Position":
        """Return a new ``Position`` reflecting a sale of ``quantity`` shares.

        Average cost is unaffected by a partial sale (only realized P&L,
        computed by the caller/use case, changes)."""

        if quantity <= Decimal("0"):
            raise InvalidQuantityError(
                f"Cannot remove a non-positive quantity of shares, got {quantity}"
            )
        if quantity > self.quantity:
            raise InsufficientSharesError(
                symbol=self.instrument.symbol, held=self.quantity, requested=quantity
            )
        return Position(
            instrument=self.instrument,
            quantity=self.quantity - quantity,
            average_cost=self.average_cost,
        )

    def is_closed(self) -> bool:
        return self.quantity == Decimal("0")
