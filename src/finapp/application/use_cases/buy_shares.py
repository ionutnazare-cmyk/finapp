"""Use case: record a purchase of shares into an existing portfolio."""

from __future__ import annotations

from decimal import Decimal

from finapp.application.exceptions import PortfolioNotFoundError
from finapp.application.ports import PortfolioRepository
from finapp.domain.entities.instrument import Instrument
from finapp.domain.entities.position import Position
from finapp.domain.value_objects.money import Money


class BuyShares:
    """Record a purchase of ``quantity`` shares of ``instrument`` at ``price``
    into the named portfolio, persisting the updated portfolio afterward.

    Raises :class:`~finapp.application.exceptions.PortfolioNotFoundError` if
    the portfolio doesn't exist. Domain invariants (currency consistency,
    non-positive quantities) are enforced by :class:`Portfolio`/`Position`
    and surface as the corresponding ``finapp.domain.exceptions`` types.
    """

    def __init__(self, portfolio_repository: PortfolioRepository) -> None:
        self._portfolio_repository = portfolio_repository

    def execute(
        self,
        portfolio_name: str,
        instrument: Instrument,
        quantity: Decimal,
        price: Money,
    ) -> Position:
        portfolio = self._portfolio_repository.get(portfolio_name)
        if portfolio is None:
            raise PortfolioNotFoundError(portfolio_name)

        position = portfolio.buy(instrument, quantity, price)
        self._portfolio_repository.save(portfolio)
        return position
