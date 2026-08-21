"""Portfolio simulation use case."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from finapp.application.ports import MarketDataProvider
from finapp.domain.portfolio import (
    Allocation,
    CashAccount,
    CorporateAction,
    LedgerTransaction,
    LedgerTransactionType,
    MonthlyHistory,
    Portfolio,
    Position,
    SimulationResult,
    TLVBonusShareGrant,
    make_position,
    money,
    purchase_quantity,
)


@dataclass
class _Holding:
    shares: Decimal = Decimal("0")
    invested: Decimal = Decimal("0.00")
    dividends: Decimal = Decimal("0.00")


class SimulationRequest(BaseModel):
    """Inputs controlling monthly investing and corporate actions."""

    model_config = ConfigDict(frozen=True)

    start_date: date
    end_date: date
    monthly_contribution: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    allocation: Allocation
    allow_fractional: bool = True
    broker_fee: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2)
    corporate_actions: tuple[CorporateAction, ...] = ()
    reinvest_dividends: bool = True

    @model_validator(mode="after")
    def validate_date_range(self) -> SimulationRequest:
        if self.end_date < self.start_date:
            raise ValueError("end date must not be before start date")
        for action in self.corporate_actions:
            if not self.start_date <= action.occurred_on <= self.end_date:
                raise ValueError(
                    "corporate action date must be inside the simulation range"
                )
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
    """Run deterministic periodic investing, dividends, and TLV bonus shares."""
    holdings: dict[str, _Holding] = {}
    transactions: list[LedgerTransaction] = []
    cash_history: list[CashAccount] = []
    monthly_history: list[MonthlyHistory] = []
    cash, fees_total = Decimal("0.00"), Decimal("0.00")
    monthly = set(monthly_dates(request.start_date, request.end_date))
    actions_by_date: dict[date, list[CorporateAction]] = {}
    for action in request.corporate_actions:
        actions_by_date.setdefault(action.occurred_on, []).append(action)

    for event_date in sorted(monthly | set(actions_by_date)):
        month_invested = Decimal("0.00")
        if event_date in monthly:
            cash += request.monthly_contribution
            for target in request.allocation.targets:
                spent, fee = _buy(
                    holdings,
                    transactions,
                    target.ticker,
                    request.allocation.amount_for(request.monthly_contribution, target),
                    event_date,
                    provider,
                    request.allow_fractional,
                    request.broker_fee,
                )
                cash -= spent
                month_invested += spent
                fees_total += fee

        for action in actions_by_date.get(event_date, []):
            if isinstance(action, TLVBonusShareGrant):
                holding = holdings.get("TLV")
                if holding is not None:
                    bonus = holding.shares * action.bonus_shares_per_share
                    holding.shares += bonus
                    transactions.append(
                        LedgerTransaction(
                            transaction_type=LedgerTransactionType.BONUS_SHARES,
                            occurred_on=event_date,
                            ticker="TLV",
                            shares=bonus,
                        )
                    )
            elif (holding := holdings.get(action.ticker)) is not None:
                received = money(
                    holding.shares
                    * action.dividend_per_share
                    * (Decimal("1") - action.withholding_tax_rate)
                )
                holding.dividends += received
                cash += received
                transactions.append(
                    LedgerTransaction(
                        transaction_type=LedgerTransactionType.DIVIDEND,
                        occurred_on=event_date,
                        ticker=action.ticker,
                        cash_received=received,
                    )
                )
                if request.reinvest_dividends:
                    spent, fee = _buy(
                        holdings,
                        transactions,
                        action.ticker,
                        received,
                        event_date,
                        provider,
                        request.allow_fractional,
                        request.broker_fee,
                    )
                    cash -= spent
                    fees_total += fee

        if event_date in monthly:
            positions = _positions(holdings, event_date, provider)
            market_value = sum(
                (position.market_value for position in positions), Decimal()
            )
            cash_account = CashAccount(
                balance=money(cash),
                unused_cash=money(cash),
                broker_fees=money(fees_total),
            )
            cash_history.append(cash_account)
            monthly_history.append(
                MonthlyHistory(
                    occurred_on=event_date,
                    contribution=request.monthly_contribution,
                    invested=money(month_invested),
                    cash_balance=cash_account.balance,
                    market_value=money(market_value),
                )
            )

    positions = _positions(holdings, request.end_date, provider)
    invested = money(sum((item.invested_amount for item in positions), Decimal()))
    market_value = money(sum((item.market_value for item in positions), Decimal()))
    dividends = sum((item.dividend_received for item in positions), Decimal())
    months = len(monthly)
    portfolio = Portfolio(
        market_value=market_value,
        cash=money(cash),
        invested=invested,
        profit=money(market_value + dividends - invested),
        annual_dividend_estimate=money(dividends / months * Decimal("12")),
        allocation=request.allocation,
        positions=positions,
    )
    return SimulationResult(
        portfolio=portfolio,
        transactions=tuple(transactions),
        cash_history=tuple(cash_history),
        monthly_history=tuple(monthly_history),
    )


def _buy(
    holdings: dict[str, _Holding],
    transactions: list[LedgerTransaction],
    ticker: str,
    budget: Decimal,
    occurred_on: date,
    provider: MarketDataProvider,
    allow_fractional: bool,
    broker_fee: Decimal,
) -> tuple[Decimal, Decimal]:
    """Purchase a ticker from a bounded cash budget and append its ledger event."""
    available = budget - broker_fee
    shares = purchase_quantity(
        available, provider.get_price(ticker, occurred_on), allow_fractional
    )
    if shares == 0:
        return Decimal("0.00"), Decimal("0.00")
    price = provider.get_price(ticker, occurred_on)
    cash_used = money(shares * price)
    total_cost = cash_used + broker_fee
    if total_cost > budget:
        raise ValueError(f"budget is insufficient for {ticker} broker fee")
    holding = holdings.setdefault(ticker, _Holding())
    holding.shares += shares
    holding.invested += total_cost
    transactions.append(
        LedgerTransaction(
            occurred_on=occurred_on,
            ticker=ticker,
            shares=shares,
            price=price,
            fees=broker_fee,
            cash_used=cash_used,
        )
    )
    return total_cost, broker_fee


def _positions(
    holdings: dict[str, _Holding], on_date: date, provider: MarketDataProvider
) -> tuple[Position, ...]:
    return tuple(
        make_position(
            ticker,
            holding.shares,
            holding.invested,
            provider.get_price(ticker, on_date),
            holding.dividends,
        )
        for ticker, holding in sorted(holdings.items())
    )
