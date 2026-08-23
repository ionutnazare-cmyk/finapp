"""The ``Dividend`` value object: an announced cash distribution per share."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, field_validator

from finapp.domain.value_objects.money import Money


class Dividend(BaseModel):
    """A dividend payment: a fixed cash amount per share, on a given pay date.

    ``Dividend`` describes the payment itself, independent of who holds the
    instrument — analogous to how a market price is independent of any one
    portfolio. Turning a ``Dividend`` into actual income for a specific
    holding is :meth:`~finapp.domain.entities.position.Position.dividend_income`,
    which multiplies by the quantity held.
    """

    model_config = ConfigDict(frozen=True)

    symbol: str
    amount_per_share: Money
    pay_date: date

    @field_validator("symbol")
    @classmethod
    def _symbol_uppercase(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("Dividend.symbol must not be blank")
        return normalized

    def __str__(self) -> str:
        return f"{self.symbol} {self.amount_per_share}/share on {self.pay_date.isoformat()}"
