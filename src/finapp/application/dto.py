"""Data-transfer objects exchanged across the application layer's ports and use cases."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator

from finapp.domain.entities.instrument import Instrument
from finapp.domain.services.monte_carlo import MonteCarloResult
from finapp.domain.services.retirement_planning import RetirementPlanResult
from finapp.domain.value_objects.bonus_issue import BonusIssue
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


@dataclass(frozen=True)
class BonusIssueApplication:
    """The outcome of applying one bonus share issue to a held position."""

    instrument: Instrument
    bonus: BonusIssue
    quantity_before: Decimal
    quantity_after: Decimal
    additional_shares: Decimal


@dataclass(frozen=True)
class PortfolioBonusIssueResult:
    """The full outcome of applying every known bonus issue across a portfolio's
    positions. Positions with no known bonus issue are simply absent from
    ``applications`` — most instruments never issue bonus shares."""

    portfolio_name: str
    applications: tuple[BonusIssueApplication, ...]


@dataclass(frozen=True)
class PortfolioMonteCarloResult:
    """A Monte Carlo simulation's outcome, tied to the portfolio it started from."""

    portfolio_name: str
    simulation: MonteCarloResult


@dataclass(frozen=True)
class PortfolioRetirementPlanResult:
    """A retirement plan's outcome, tied to the portfolio it started from."""

    portfolio_name: str
    plan: RetirementPlanResult


@dataclass(frozen=True)
class PortfolioReport:
    """Aggregated data for exporting a portfolio report (Excel/PDF).

    Bundles valuation and (optional) dividend income together so both
    export formats render from exactly the same figures, computed once —
    an Excel and a PDF export of the same portfolio at the same moment
    will always agree.
    """

    portfolio_name: str
    generated_at: datetime
    valuation: PortfolioValuation
    dividend_income: PortfolioDividendIncome | None = None


@dataclass(frozen=True)
class MarketDataRefreshResult:
    """Outcome of a (possibly skipped) BVB data refresh attempt.

    ``attempted`` is ``False`` when the freshness policy decided a refresh
    wasn't due yet — everything else is then empty/reflects no work done.
    """

    attempted: bool
    updated_symbols: tuple[str, ...]
    failed_symbols: tuple[str, ...]
    as_of: datetime
