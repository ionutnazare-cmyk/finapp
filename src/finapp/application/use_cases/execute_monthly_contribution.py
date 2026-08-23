"""Use case: execute a monthly DCA (dollar-cost averaging) contribution."""

from __future__ import annotations

from decimal import Decimal

from finapp.application.dto import (
    DcaAllocationResult,
    MonthlyContributionRequest,
    MonthlyContributionResult,
)
from finapp.application.exceptions import (
    InvalidAllocationError,
    PortfolioNotFoundError,
    QuoteNotFoundError,
)
from finapp.application.ports import MarketDataProvider, PortfolioRepository
from finapp.domain.exceptions import CurrencyMismatchError

_WEIGHT_TOLERANCE = Decimal("0.0001")


class ExecuteMonthlyContribution:
    """Split a fixed monthly contribution across a target allocation and buy
    the corresponding shares at current market prices — dollar-cost
    averaging into a portfolio.

    The allocation's weights must be positive and sum to 1 (within a small
    tolerance); this use case validates the allocation rather than trying to
    normalize or "fix" it, so a caller's mistake surfaces immediately.
    Fractional share quantities are allowed: FinApp models the ideal target
    allocation here, not brokerage order-lot/rounding mechanics.
    """

    def __init__(
        self,
        portfolio_repository: PortfolioRepository,
        market_data_provider: MarketDataProvider,
    ) -> None:
        self._portfolio_repository = portfolio_repository
        self._market_data_provider = market_data_provider

    def execute(self, request: MonthlyContributionRequest) -> MonthlyContributionResult:
        portfolio = self._portfolio_repository.get(request.portfolio_name)
        if portfolio is None:
            raise PortfolioNotFoundError(request.portfolio_name)

        self._validate_allocation(request)

        if request.contribution.currency != portfolio.base_currency:
            raise CurrencyMismatchError(
                expected=portfolio.base_currency.value,
                actual=request.contribution.currency.value,
            )

        quotes = self._market_data_provider.get_quotes(
            instrument.symbol for instrument in request.allocation
        )

        allocation_results: list[DcaAllocationResult] = []
        for instrument, weight in request.allocation.items():
            quote = quotes.get(instrument.symbol)
            if quote is None:
                raise QuoteNotFoundError(instrument.symbol)

            allocated_cash = request.contribution * weight
            quantity = allocated_cash.amount / quote.price.amount
            portfolio.buy(instrument, quantity, quote.price)

            allocation_results.append(
                DcaAllocationResult(
                    instrument=instrument,
                    weight=weight,
                    allocated_cash=allocated_cash,
                    price=quote.price,
                    quantity_purchased=quantity,
                )
            )

        self._portfolio_repository.save(portfolio)

        return MonthlyContributionResult(
            portfolio_name=portfolio.name,
            total_contribution=request.contribution,
            allocations=tuple(allocation_results),
        )

    @staticmethod
    def _validate_allocation(request: MonthlyContributionRequest) -> None:
        if not request.allocation:
            raise InvalidAllocationError("Allocation must contain at least one instrument")

        total_weight = Decimal("0")
        for instrument, weight in request.allocation.items():
            if weight <= Decimal("0"):
                raise InvalidAllocationError(
                    f"Allocation weight for {instrument.symbol} must be positive, got {weight}"
                )
            total_weight += weight

        if abs(total_weight - Decimal("1")) > _WEIGHT_TOLERANCE:
            raise InvalidAllocationError(
                f"Allocation weights must sum to 1 (within {_WEIGHT_TOLERANCE}), "
                f"got {total_weight}"
            )
