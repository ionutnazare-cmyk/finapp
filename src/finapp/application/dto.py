"""Data-transfer objects exchanged across the application layer's ports and use cases."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator

from finapp.domain.entities.instrument import Instrument
from finapp.domain.value_objects.dividend import Dividend
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


@dataclass(frozen=True)
class MonthlyContributionRequest:
    """A request to split a fixed monthly contribution across a target
    allocation and buy the corresponding shares ("dollar-cost averaging").

    ``allocation`` maps each target :class:`Instrument` to its target weight
    (a fraction of the total contribution); weights must be positive and sum
    to 1, which :class:`~finapp.application.use_cases.execute_monthly_contribution.ExecuteMonthlyContribution`
    validates before doing anything else.
    """

    portfolio_name: str
    contribution: Money
    allocation: Mapping[Instrument, Decimal]


@dataclass(frozen=True)
class DcaAllocationResult:
    """The outcome of buying one instrument's share of a monthly contribution."""

    instrument: Instrument
    weight: Decimal
    allocated_cash: Money
    price: Money
    quantity_purchased: Decimal


@dataclass(frozen=True)
class MonthlyContributionResult:
    """The full outcome of executing a :class:`MonthlyContributionRequest`."""

    portfolio_name: str
    total_contribution: Money
    allocations: tuple[DcaAllocationResult, ...]


@dataclass(frozen=True)
class DividendIncome:
    """Income from one position's most recent known dividend."""

    instrument: Instrument
    quantity_held: Decimal
    dividend: Dividend
    total_income: Money


@dataclass(frozen=True)
class PortfolioDividendIncome:
    """A portfolio's total dividend income across all positions with a known dividend.

    Positions with no known dividend history are simply excluded from
    ``incomes`` — that's the normal case for non-dividend-paying holdings,
    not an error.
    """

    portfolio_name: str
    base_currency_total_income: Money
    incomes: tuple[DividendIncome, ...]


@dataclass(frozen=True)
class DividendReinvestment:
    """The outcome of reinvesting one position's dividend income back into
    more shares of the same instrument (a DRIP — dividend reinvestment plan)."""

    instrument: Instrument
    dividend_income: Money
    price: Money
    quantity_purchased: Decimal


@dataclass(frozen=True)
class DividendReinvestmentResult:
    """The full outcome of reinvesting all available dividend income in a portfolio."""

    portfolio_name: str
    base_currency_total_reinvested: Money
    reinvestments: tuple[DividendReinvestment, ...]
