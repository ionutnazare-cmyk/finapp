"""Command-line interface for FinApp."""

from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from finapp.application.simulate_portfolio import SimulationRequest, simulate_portfolio
from finapp.domain.portfolio import Allocation, AllocationTarget
from finapp.infrastructure.static_prices import StaticPriceProvider


def main() -> None:
    """Execute the FinApp command-line interface."""
    parser = argparse.ArgumentParser(prog="finapp")
    commands = parser.add_subparsers(dest="command", required=True)
    simulation = commands.add_parser("simulate", help="simulate monthly investing")
    simulation.add_argument("--from", dest="start", required=True, help="YYYY-MM")
    simulation.add_argument("--to", dest="end", required=True, help="YYYY-MM")
    simulation.add_argument("--monthly", required=True, type=Decimal)
    simulation.add_argument("--allocation", required=True)
    simulation.add_argument("--prices", type=Path, default=Path("prices.json"))
    simulation.add_argument("--whole-shares", action="store_true")
    simulation.add_argument("--broker-fee", type=Decimal, default=Decimal("0.00"))
    args = parser.parse_args()
    if args.command == "simulate":
        _simulate(args)


def _simulate(args: argparse.Namespace) -> None:
    try:
        request = SimulationRequest(
            start_date=_month(args.start),
            end_date=_month(args.end),
            monthly_contribution=args.monthly,
            allocation=_allocation(args.allocation),
            allow_fractional=not args.whole_shares,
            broker_fee=args.broker_fee,
        )
        result = simulate_portfolio(request, StaticPriceProvider.from_json(args.prices))
    except (OSError, ValueError, InvalidOperation) as error:
        raise SystemExit(f"Simulation failed: {error}") from error

    portfolio = result.portfolio
    print("Portfolio Summary")
    print(f"Market value: {portfolio.market_value:.2f} RON")
    print(f"Cash: {portfolio.cash:.2f} RON")
    print(f"Invested: {portfolio.invested:.2f} RON")
    print(f"Profit: {portfolio.profit:.2f} RON")
    print("\nAllocation")
    for target in portfolio.allocation.targets:
        print(f"{target.ticker}: {target.percentage}%")
    print("\nTransactions")
    for transaction in result.transactions:
        print(
            f"{transaction.occurred_on} BUY {transaction.ticker} "
            f"{transaction.shares} @ {transaction.price:.2f} RON"
        )


def _month(value: str) -> date:
    try:
        year_text, month_text = value.split("-", maxsplit=1)
        return date(int(year_text), int(month_text), 1)
    except ValueError as error:
        raise ValueError(f"invalid month {value!r}; expected YYYY-MM") from error


def _allocation(value: str) -> Allocation:
    targets: list[AllocationTarget] = []
    try:
        for item in value.split(","):
            ticker, percentage = item.split("=", maxsplit=1)
            targets.append(
                AllocationTarget(ticker=ticker, percentage=Decimal(percentage))
            )
    except (InvalidOperation, ValueError) as error:
        raise ValueError("allocation must look like TLV=40,SNP=35,H2O=25") from error
    return Allocation(targets=tuple(targets))
