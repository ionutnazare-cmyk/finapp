from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from finapp.application.simulate_portfolio import SimulationRequest, simulate_portfolio
from finapp.domain.portfolio import (
    Allocation,
    AllocationTarget,
    DividendPayment,
    LedgerTransactionType,
    TLVBonusShareGrant,
)
from finapp.infrastructure.static_prices import StaticPriceProvider


def allocation(*targets: tuple[str, str]) -> Allocation:
    return Allocation(
        targets=tuple(
            AllocationTarget(ticker=ticker, percentage=Decimal(percentage))
            for ticker, percentage in targets
        )
    )


def provider_for_months(
    tickers: dict[str, str], start_year: int, start_month: int, count: int
) -> StaticPriceProvider:
    prices: dict[str, dict[str, Decimal]] = {ticker: {} for ticker in tickers}
    year, month = start_year, start_month
    for _ in range(count):
        when = date(year, month, 1).isoformat()
        for ticker, price in tickers.items():
            prices[ticker][when] = Decimal(price)
        month += 1
        if month == 13:
            year, month = year + 1, 1
    return StaticPriceProvider(prices)


def test_allocation_requires_exactly_one_hundred_percent() -> None:
    with pytest.raises(ValidationError, match="total exactly 100"):
        allocation(("TLV", "40"), ("SNP", "35"))


def test_allocation_rejects_duplicate_tickers() -> None:
    with pytest.raises(ValidationError, match="unique"):
        allocation(("TLV", "50"), ("tlv", "50"))


def test_fractional_purchase_updates_position_and_average_cost() -> None:
    result = simulate_portfolio(
        SimulationRequest(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 1),
            monthly_contribution=Decimal("100"),
            allocation=allocation(("TLV", "100")),
        ),
        provider_for_months({"TLV": "40"}, 2026, 1, 1),
    )

    position = result.portfolio.positions[0]
    assert position.shares == Decimal("2.50000000")
    assert position.average_cost == Decimal("40.00")
    assert position.invested_amount == Decimal("100.00")
    assert position.market_value == Decimal("100.00")
    assert position.profit == Decimal("0.00")
    assert result.transactions[0].cash_used == Decimal("100.00")
    assert result.portfolio.cash == Decimal("0.00")


def test_whole_share_purchase_retains_unused_cash() -> None:
    result = simulate_portfolio(
        SimulationRequest(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 1),
            monthly_contribution=Decimal("100"),
            allocation=allocation(("TLV", "100")),
            allow_fractional=False,
        ),
        provider_for_months({"TLV": "30"}, 2026, 1, 1),
    )

    position = result.portfolio.positions[0]
    assert position.shares == Decimal("3")
    assert position.average_cost == Decimal("30.00")
    assert result.portfolio.invested == Decimal("90.00")
    assert result.portfolio.cash == Decimal("10.00")
    assert result.cash_history[0].unused_cash == Decimal("10.00")


def test_cash_account_records_broker_fees() -> None:
    result = simulate_portfolio(
        SimulationRequest(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 1),
            monthly_contribution=Decimal("100"),
            allocation=allocation(("TLV", "100")),
            broker_fee=Decimal("5"),
        ),
        provider_for_months({"TLV": "19"}, 2026, 1, 1),
    )

    transaction = result.transactions[0]
    assert transaction.fees == Decimal("5.00")
    assert transaction.cash_used == Decimal("95.00")
    assert result.cash_history[0].broker_fees == Decimal("5.00")
    assert result.portfolio.cash == Decimal("0.00")


def test_twenty_four_month_simulation_has_correct_positions_and_ledger() -> None:
    result = simulate_portfolio(
        SimulationRequest(
            start_date=date(2026, 1, 1),
            end_date=date(2027, 12, 1),
            monthly_contribution=Decimal("4000"),
            allocation=allocation(("TLV", "40"), ("SNP", "35"), ("H2O", "25")),
        ),
        provider_for_months({"TLV": "40", "SNP": "0.85", "H2O": "120"}, 2026, 1, 24),
    )

    positions = {position.ticker: position for position in result.portfolio.positions}
    assert len(result.transactions) == 72
    assert len(result.monthly_history) == 24
    assert positions["TLV"].shares == Decimal("960.00000000")
    assert positions["TLV"].average_cost == Decimal("40.00")
    assert positions["H2O"].shares == Decimal("199.99999992")
    assert positions["SNP"].average_cost == Decimal("0.85")
    assert result.portfolio.invested == Decimal("96000.00")
    assert result.portfolio.cash == Decimal("0.00")
    assert result.portfolio.profit == Decimal("0.00")


def test_dividend_is_recorded_and_reinvested_in_the_same_ticker() -> None:
    provider = StaticPriceProvider(
        {
            "SNP": {
                "2026-01-01": Decimal("10"),
                "2026-01-15": Decimal("10"),
                "2026-01-31": Decimal("10"),
            }
        }
    )
    result = simulate_portfolio(
        SimulationRequest(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            monthly_contribution=Decimal("100"),
            allocation=allocation(("SNP", "100")),
            corporate_actions=(
                DividendPayment(
                    occurred_on=date(2026, 1, 15),
                    ticker="SNP",
                    dividend_per_share=Decimal("1"),
                ),
            ),
        ),
        provider,
    )

    position = result.portfolio.positions[0]
    assert position.shares == Decimal("11.00000000")
    assert position.dividend_received == Decimal("10.00")
    assert result.portfolio.cash == Decimal("0.00")
    assert [item.transaction_type for item in result.transactions] == [
        LedgerTransactionType.BUY,
        LedgerTransactionType.DIVIDEND,
        LedgerTransactionType.BUY,
    ]


def test_tlv_bonus_shares_increase_shares_without_increasing_investment() -> None:
    provider = StaticPriceProvider(
        {
            "TLV": {
                "2026-01-01": Decimal("10"),
                "2026-01-15": Decimal("10"),
                "2026-01-31": Decimal("10"),
            }
        }
    )
    result = simulate_portfolio(
        SimulationRequest(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            monthly_contribution=Decimal("100"),
            allocation=allocation(("TLV", "100")),
            corporate_actions=(
                TLVBonusShareGrant(
                    occurred_on=date(2026, 1, 15),
                    bonus_shares_per_share=Decimal("0.1"),
                ),
            ),
        ),
        provider,
    )

    position = result.portfolio.positions[0]
    assert position.shares == Decimal("11.00000000")
    assert position.invested_amount == Decimal("100.00")
    assert position.average_cost == Decimal("9.09")
    assert (
        result.transactions[-1].transaction_type is LedgerTransactionType.BONUS_SHARES
    )
