"""Pure portfolio simulation models and calculations."""

from __future__ import annotations

from datetime import date
from decimal import ROUND_DOWN, Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MONEY_QUANTUM = Decimal("0.01")
PERCENT_QUANTUM = Decimal("0.0001")


def money(value: Decimal) -> Decimal:
    """Round a monetary value to Romanian ban precision."""
    return value.quantize(MONEY_QUANTUM)


class AllocationTarget(BaseModel):
    """The percentage of a contribution assigned to one ticker."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    ticker: str = Field(min_length=1, max_length=20)
    percentage: Decimal = Field(gt=0, le=100, max_digits=7, decimal_places=4)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.upper()


class Allocation(BaseModel):
    """A complete investment allocation."""

    model_config = ConfigDict(frozen=True)

    targets: tuple[AllocationTarget, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_total_and_tickers(self) -> Allocation:
        total = sum((target.percentage for target in self.targets), Decimal())
        if total != Decimal("100"):
            raise ValueError("allocation percentages must total exactly 100")
        tickers = [target.ticker for target in self.targets]
        if len(tickers) != len(set(tickers)):
            raise ValueError("allocation tickers must be unique")
        return self

    def amount_for(self, contribution: Decimal, target: AllocationTarget) -> Decimal:
        """Return the money budget for an allocation target."""
        return money(contribution * target.percentage / Decimal("100"))


class CashAccount(BaseModel):
    """Cash retained by the portfolio and cumulative broker fees."""

    model_config = ConfigDict(frozen=True)

    balance: Decimal = Decimal("0.00")
    unused_cash: Decimal = Decimal("0.00")
    broker_fees: Decimal = Decimal("0.00")


class Position(BaseModel):
    """A portfolio holding with derived performance values."""

    model_config = ConfigDict(frozen=True)

    ticker: str
    shares: Decimal
    average_cost: Decimal
    invested_amount: Decimal
    market_value: Decimal
    profit: Decimal
    profit_percent: Decimal
    dividend_received: Decimal = Decimal("0.00")
    yield_on_cost: Decimal = Decimal("0.00")


class LedgerTransactionType(StrEnum):
    """Supported investment ledger events."""

    BUY = "BUY"


class LedgerTransaction(BaseModel):
    """An executed market order stored in the transaction ledger."""

    model_config = ConfigDict(frozen=True)

    transaction_type: LedgerTransactionType = LedgerTransactionType.BUY
    occurred_on: date
    ticker: str
    shares: Decimal = Field(gt=0)
    price: Decimal = Field(gt=0)
    fees: Decimal = Field(ge=0)
    cash_used: Decimal = Field(gt=0)


class MonthlyHistory(BaseModel):
    """End-of-month simulation snapshot."""

    model_config = ConfigDict(frozen=True)

    occurred_on: date
    contribution: Decimal
    invested: Decimal
    cash_balance: Decimal
    market_value: Decimal


class Portfolio(BaseModel):
    """Aggregate portfolio state after a simulation."""

    model_config = ConfigDict(frozen=True)

    market_value: Decimal
    cash: Decimal
    invested: Decimal
    profit: Decimal
    annual_dividend_estimate: Decimal
    allocation: Allocation
    positions: tuple[Position, ...]


class SimulationResult(BaseModel):
    """Complete, reproducible output of a portfolio simulation."""

    model_config = ConfigDict(frozen=True)

    portfolio: Portfolio
    transactions: tuple[LedgerTransaction, ...]
    cash_history: tuple[CashAccount, ...]
    monthly_history: tuple[MonthlyHistory, ...]


def purchase_quantity(
    available_cash: Decimal, price: Decimal, allow_fractional: bool
) -> Decimal:
    """Calculate purchasable shares without using binary floating-point arithmetic."""
    if available_cash <= 0 or price <= 0:
        return Decimal("0")
    raw_quantity = available_cash / price
    if allow_fractional:
        return raw_quantity.quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)
    return raw_quantity.quantize(Decimal("1"), rounding=ROUND_DOWN)


def make_position(
    ticker: str,
    shares: Decimal,
    invested_amount: Decimal,
    current_price: Decimal,
    dividend_received: Decimal = Decimal("0.00"),
) -> Position:
    """Build a position and all of its derived values."""
    market_value = money(shares * current_price)
    average_cost = money(invested_amount / shares) if shares else Decimal("0.00")
    profit = money(market_value + dividend_received - invested_amount)
    profit_percent = (
        (profit / invested_amount * Decimal("100")).quantize(PERCENT_QUANTUM)
        if invested_amount
        else Decimal("0.0000")
    )
    yield_on_cost = (
        (dividend_received / invested_amount * Decimal("100")).quantize(PERCENT_QUANTUM)
        if invested_amount
        else Decimal("0.0000")
    )
    return Position(
        ticker=ticker,
        shares=shares,
        average_cost=average_cost,
        invested_amount=invested_amount,
        market_value=market_value,
        profit=profit,
        profit_percent=profit_percent,
        dividend_received=dividend_received,
        yield_on_cost=yield_on_cost,
    )
