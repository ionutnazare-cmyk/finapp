"""Data-transfer objects exchanged across the application layer's ports and use cases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

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


@dataclass(frozen=True)
class PositionValuation:
    """A single position's valuation as of a given quote.

    A plain (non-pydantic) frozen dataclass, since this is an internal
    computation result assembled by a use case rather than data crossing
    a validated boundary (e.g. an external API or a repository).
    """

    symbol: str
    quantity: Decimal
    average_cost: Money
    market_price: Money
    book_cost: Money
    market_value: Money
    unrealized_pnl: Money


@dataclass(frozen=True)
class PortfolioValuation:
    """The full valuation of a portfolio: totals plus a per-position breakdown."""

    portfolio_name: str
    base_currency_total_book_cost: Money
    base_currency_total_market_value: Money
    base_currency_total_unrealized_pnl: Money
    positions: tuple[PositionValuation, ...]
