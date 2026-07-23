"""Portfolio simulation use case."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from finapp.application.ports import MarketDataProvider
from finapp.domain.portfolio import (
    Allocation,
    CashAccount,
    LedgerTransaction,
    MonthlyHistory,
    Portfolio,
    Position,
    SimulationResult,
    make_position,
    money,
    purchase_quantity,
)


class SimulationRequest(BaseModel):
    """Inputs controlling a monthly portfolio simulation."""

    model_config = ConfigDict(frozen=True)

    start_date: date
    end_date: date
    monthly_contribution: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    allocation: Allocation
    allow_fractional: bool = True
    broker_fee: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2)

    @model_validator(mode="after")
    def validate_date_range(self) -> SimulationRequest:
        if self.end_date < self.start_date:
            raise ValueError("end date must not be before start date")
        return self


def monthly_dates(start_date: date, end_date: date) -> tuple[date, ...]:
    """Return one investment date per calendar month, inclusive."""
    dates: list[date] = []
    year, month = start_date.year, start_date.month
    while (year, month) <= (end_date.year, end_date.month):
        dates.append(date(year, month, 1))
        month += 1
        if month == 13:
            year, month = year + 1, 1
    return tuple(dates)


def simulate_portfolio(
    request: SimulationRequest, provider: MarketDataProvider
) -> SimulationResult:
    """Run deterministic periodic investing with the supplied market data provider."""
    states: dict[str, tuple[Decimal, Decimal]] = {}
    transactions: list[LedgerTransaction] = []
    cash_history: list[CashAccount] = []
    monthly_history: list[MonthlyHistory] = []
    cash = Decimal("0.00")
    fees_total = Decimal("0.00")
    last_prices: dict[str, Decimal] = {}

    for investment_date in monthly_dates(request.start_date, request.end_date):
        cash += request.monthly_contribution
        month_invested = Decimal("0.00")
        for target in request.allocation.targets:
            budget = request.allocation.amount_for(request.monthly_contribution, target)
            price = provider.get_price(target.ticker, investment_date)
            if price <= 0:
                raise ValueError(f"price for {target.ticker} must be positive")
            available_for_shares = budget - request.broker_fee
            shares = purchase_quantity(
                available_for_shares, price, request.allow_fractional
            )
            if shares == 0:
                continue
            cash_used = money(shares * price)
            fees = request.broker_fee
            total_cost = cash_used + fees
            if total_cost > budget:
                raise ValueError(
                    f"budget is insufficient for {target.ticker} broker fee"
                )
            old_shares, old_invested = states.get(
                target.ticker, (Decimal("0"), Decimal("0.00"))
            )
            states[target.ticker] = (old_shares + shares, old_invested + total_cost)
            cash -= total_cost
            month_invested += total_cost
            fees_total += fees
            last_prices[target.ticker] = price
            transactions.append(
                LedgerTransaction(
                    occurred_on=investment_date,
                    ticker=target.ticker,
                    shares=shares,
                    price=price,
                    fees=fees,
                    cash_used=cash_used,
                )
            )

        positions = _positions(states, last_prices)
        market_value = sum((position.market_value for position in positions), Decimal())
        cash_account = CashAccount(
            balance=money(cash), unused_cash=money(cash), broker_fees=money(fees_total)
        )
        cash_history.append(cash_account)
        monthly_history.append(
            MonthlyHistory(
                occurred_on=investment_date,
                contribution=request.monthly_contribution,
                invested=money(month_invested),
                cash_balance=cash_account.balance,
                market_value=money(market_value),
            )
        )

    positions = _positions(states, last_prices)
    invested = money(
        sum((position.invested_amount for position in positions), Decimal())
    )
    market_value = money(
        sum((position.market_value for position in positions), Decimal())
    )
    dividends = sum((position.dividend_received for position in positions), Decimal())
    portfolio = Portfolio(
        market_value=market_value,
        cash=money(cash),
        invested=invested,
        profit=money(market_value + dividends - invested),
        annual_dividend_estimate=Decimal("0.00"),
        allocation=request.allocation,
        positions=positions,
    )
    return SimulationResult(
        portfolio=portfolio,
        transactions=tuple(transactions),
        cash_history=tuple(cash_history),
        monthly_history=tuple(monthly_history),
    )


def _positions(
    states: dict[str, tuple[Decimal, Decimal]], last_prices: dict[str, Decimal]
) -> tuple[Position, ...]:
    return tuple(
        make_position(ticker, shares, invested, last_prices[ticker])
        for ticker, (shares, invested) in sorted(states.items())
    )
