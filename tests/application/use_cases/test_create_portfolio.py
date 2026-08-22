from __future__ import annotations

import pytest

from finapp.application.exceptions import PortfolioAlreadyExistsError
from finapp.application.use_cases.create_portfolio import CreatePortfolio
from finapp.domain.value_objects.enums import Currency
from finapp.infrastructure.repositories.in_memory_portfolio_repository import (
    InMemoryPortfolioRepository,
)


def test_creates_and_persists_empty_portfolio() -> None:
    repository = InMemoryPortfolioRepository()
    use_case = CreatePortfolio(repository)

    portfolio = use_case.execute("Retirement", Currency.RON)

    assert portfolio.name == "Retirement"
    assert portfolio.base_currency == Currency.RON
    assert portfolio.is_empty()
    assert repository.get("Retirement") is portfolio


def test_duplicate_name_raises() -> None:
    repository = InMemoryPortfolioRepository()
    use_case = CreatePortfolio(repository)
    use_case.execute("Retirement", Currency.RON)

    with pytest.raises(PortfolioAlreadyExistsError):
        use_case.execute("Retirement", Currency.RON)
