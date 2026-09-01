"""Use case: directly correct a held position's quantity and average cost."""

from __future__ import annotations

from decimal import Decimal

from finapp.application.exceptions import PortfolioNotFoundError
from finapp.application.ports import PortfolioRepository
from finapp.domain.entities.position import Position
from finapp.domain.value_objects.money import Money


class EditPosition:
    """Directly correct a held position's quantity and average cost.

    Unlike :class:`~finapp.application.use_cases.buy_shares.BuyShares` and
    :class:`~finapp.application.use_cases.sell_shares.SellShares`, this
    bypasses weighted-average-cost and reduced-shares math entirely — it's
    for fixing data-entry mistakes or recording a cost basis for shares
    acquired before using FinApp, not for recording new buy/sell
    transactions.
    """

    def __init__(self, portfolio_repository: PortfolioRepository) -> None:
        self._portfolio_repository = portfolio_repository

    def execute(
        self,
        portfolio_name: str,
        symbol: str,
        quantity: Decimal,
        average_cost: Money,
    ) -> Position | None:
        portfolio = self._portfolio_repository.get(portfolio_name)
        if portfolio is None:
            raise PortfolioNotFoundError(portfolio_name)

        result = portfolio.set_position_amounts(symbol, quantity, average_cost)
        self._portfolio_repository.save(portfolio)
        return result
