"""Use case: compute a portfolio's current dividend income."""

from __future__ import annotations

from finapp.application.dto import DividendIncome, PortfolioDividendIncome
from finapp.application.exceptions import PortfolioNotFoundError
from finapp.application.ports import DividendProvider, PortfolioRepository
from finapp.domain.value_objects.money import Money


class GetPortfolioDividendIncome:
    """Compute a portfolio's dividend income based on each position's most
    recently known dividend and the quantity currently held.

    Positions with no known dividend history are excluded from the result
    rather than treated as an error — most instruments simply don't pay a
    dividend, and that's expected, not a failure.
    """

    def __init__(
        self,
        portfolio_repository: PortfolioRepository,
        dividend_provider: DividendProvider,
    ) -> None:
        self._portfolio_repository = portfolio_repository
        self._dividend_provider = dividend_provider

    def execute(self, portfolio_name: str) -> PortfolioDividendIncome:
        portfolio = self._portfolio_repository.get(portfolio_name)
        if portfolio is None:
            raise PortfolioNotFoundError(portfolio_name)

        incomes: list[DividendIncome] = []
        total = Money.zero(portfolio.base_currency)

        for symbol, position in portfolio.positions.items():
            dividend = self._dividend_provider.get_latest_dividend(symbol)
            if dividend is None:
                continue

            income = position.dividend_income(dividend)
            incomes.append(
                DividendIncome(
                    instrument=position.instrument,
                    quantity_held=position.quantity,
                    dividend=dividend,
                    total_income=income,
                )
            )
            total = total + income

        return PortfolioDividendIncome(
            portfolio_name=portfolio.name,
            base_currency_total_income=total,
            incomes=tuple(incomes),
        )
