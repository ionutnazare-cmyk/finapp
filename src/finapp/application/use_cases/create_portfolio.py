"""Use case: create a new, empty portfolio."""

from __future__ import annotations

from finapp.application.exceptions import PortfolioAlreadyExistsError
from finapp.application.ports import PortfolioRepository
from finapp.domain.entities.portfolio import Portfolio
from finapp.domain.value_objects.enums import Currency


class CreatePortfolio:
    """Create and persist a new, empty :class:`Portfolio`.

    Raises :class:`~finapp.application.exceptions.PortfolioAlreadyExistsError`
    if a portfolio with the same name is already stored.
    """

    def __init__(self, portfolio_repository: PortfolioRepository) -> None:
        self._portfolio_repository = portfolio_repository

    def execute(self, name: str, base_currency: Currency) -> Portfolio:
        if self._portfolio_repository.get(name) is not None:
            raise PortfolioAlreadyExistsError(name)

        portfolio = Portfolio(name=name, base_currency=base_currency)
        self._portfolio_repository.save(portfolio)
        return portfolio
