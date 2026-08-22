"""An in-memory :class:`PortfolioRepository`, useful for tests and demos."""

from __future__ import annotations

from collections.abc import Sequence

from finapp.application.ports import PortfolioRepository
from finapp.domain.entities.portfolio import Portfolio


class InMemoryPortfolioRepository(PortfolioRepository):
    """A :class:`PortfolioRepository` backed by a plain in-memory dict.

    Portfolios are not persisted across process restarts; use
    :class:`~finapp.infrastructure.repositories.json_portfolio_repository.JsonPortfolioRepository`
    for that. This adapter exists primarily so use cases can be exercised in
    tests without touching the filesystem.
    """

    def __init__(self) -> None:
        self._portfolios: dict[str, Portfolio] = {}

    def get(self, name: str) -> Portfolio | None:
        return self._portfolios.get(name)

    def save(self, portfolio: Portfolio) -> None:
        self._portfolios[portfolio.name] = portfolio

    def list_names(self) -> Sequence[str]:
        return tuple(sorted(self._portfolios))
