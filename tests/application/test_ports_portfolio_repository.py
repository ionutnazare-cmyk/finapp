from __future__ import annotations

import pytest

from finapp.application.ports import PortfolioRepository
from finapp.domain.entities.portfolio import Portfolio
from finapp.domain.value_objects.enums import Currency


def test_portfolio_repository_cannot_be_instantiated_directly() -> None:
    with pytest.raises(TypeError):
        PortfolioRepository()  # type: ignore[abstract]


class _FakeRepository(PortfolioRepository):
    def __init__(self) -> None:
        self._store: dict[str, Portfolio] = {}

    def get(self, name: str) -> Portfolio | None:
        return self._store.get(name)

    def save(self, portfolio: Portfolio) -> None:
        self._store[portfolio.name] = portfolio

    def list_names(self) -> tuple[str, ...]:
        return tuple(sorted(self._store))


def test_fake_repository_round_trips_a_portfolio() -> None:
    repository = _FakeRepository()
    portfolio = Portfolio(name="Retirement", base_currency=Currency.RON)
    repository.save(portfolio)
    assert repository.get("Retirement") is portfolio
    assert repository.list_names() == ("Retirement",)


def test_fake_repository_returns_none_for_missing_portfolio() -> None:
    repository = _FakeRepository()
    assert repository.get("Nonexistent") is None
