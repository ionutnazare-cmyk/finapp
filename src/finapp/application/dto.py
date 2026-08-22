"""Data-transfer objects exchanged across the application layer's ports."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, field_validator

from finapp.domain.value_objects.money import Money


class Quote(BaseModel):
    """A single price observation for an instrument at a point in time.

    ``Quote`` is an application-layer DTO, not a domain entity: it represents
    what a :class:`~finapp.application.ports.MarketDataProvider` hands back,
    not a core business concept the domain model itself needs to know about.
    Use cases translate quotes into the ``Money`` prices that
    :class:`~finapp.domain.entities.portfolio.Portfolio` methods expect.
    """

    model_config = ConfigDict(frozen=True)

    symbol: str
    price: Money
    as_of: date

    @field_validator("symbol")
    @classmethod
    def _symbol_uppercase(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("Quote.symbol must not be blank")
        return normalized

    def __str__(self) -> str:
        return f"{self.symbol}={self.price} @ {self.as_of.isoformat()}"
