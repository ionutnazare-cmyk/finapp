"""Use case: record a sale of shares from an existing portfolio."""

from __future__ import annotations

from decimal import Decimal

from finapp.application.exceptions import PortfolioNotFoundError
from finapp.application.ports import PortfolioRepository
from finapp.domain.entities.position import Position


class SellShares:
    """Record a sale of ``quantity`` shares of ``symbol`` from the named
    portfolio, persisting the updated portfolio afterward.

    Returns the resulting :class:`Position`, or ``None`` if the position was
    fully closed. Raises
    :class:`~finapp.application.exceptions.PortfolioNotFoundError` if the
    portfolio doesn't exist; raises
    :class:`~finapp.domain.exceptions.UnknownInstrumentError` or
    :class:`~finapp.domain.exceptions.InsufficientSharesError` for invalid
    sales, per :meth:`Portfolio.sell`.
    """

    def __init__(self, portfolio_repository: PortfolioRepository) -> None:
        self._portfolio_repository = portfolio_repository

    def execute(self, portfolio_name: str, symbol: str, quantity: Decimal) -> Position | None:
        portfolio = self._portfolio_repository.get(portfolio_name)
        if portfolio is None:
            raise PortfolioNotFoundError(portfolio_name)

        result = portfolio.sell(symbol, quantity)
        self._portfolio_repository.save(portfolio)
        return result
