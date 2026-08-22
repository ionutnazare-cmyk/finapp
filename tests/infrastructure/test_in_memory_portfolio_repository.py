from __future__ import annotations

from finapp.domain.entities.portfolio import Portfolio
from finapp.domain.value_objects.enums import Currency
from finapp.infrastructure.repositories.in_memory_portfolio_repository import (
    InMemoryPortfolioRepository,
)


def test_save_and_get_round_trip() -> None:
    repository = InMemoryPortfolioRepository()
    portfolio = Portfolio(name="Retirement", base_currency=Currency.RON)

    repository.save(portfolio)

    assert repository.get("Retirement") is portfolio


def test_get_missing_returns_none() -> None:
    repository = InMemoryPortfolioRepository()
    assert repository.get("Nonexistent") is None


def test_list_names_sorted() -> None:
    repository = InMemoryPortfolioRepository()
    repository.save(Portfolio(name="Zeta", base_currency=Currency.RON))
    repository.save(Portfolio(name="Alpha", base_currency=Currency.RON))

    assert repository.list_names() == ("Alpha", "Zeta")


def test_save_overwrites_existing_entry() -> None:
    repository = InMemoryPortfolioRepository()
    first = Portfolio(name="Retirement", base_currency=Currency.RON)
    second = Portfolio(name="Retirement", base_currency=Currency.EUR)

    repository.save(first)
    repository.save(second)

    stored = repository.get("Retirement")
    assert stored is second
    assert stored.base_currency == Currency.EUR  # type: ignore[union-attr]
