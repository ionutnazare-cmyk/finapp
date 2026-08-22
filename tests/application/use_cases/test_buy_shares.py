from __future__ import annotations

from decimal import Decimal

import pytest

from finapp.application.exceptions import PortfolioNotFoundError
from finapp.application.use_cases.buy_shares import BuyShares
from finapp.domain.entities.instrument import Instrument
from finapp.domain.entities.portfolio import Portfolio
from finapp.domain.exceptions import CurrencyMismatchError
from finapp.domain.value_objects.enums import AssetType, Currency
from finapp.domain.value_objects.money import Money
from finapp.infrastructure.repositories.in_memory_portfolio_repository import (
    InMemoryPortfolioRepository,
)


@pytest.fixture
def tlv() -> Instrument:
    return Instrument(
        symbol="TLV",
        name="Banca Transilvania",
        currency=Currency.RON,
        asset_type=AssetType.EQUITY,
    )


def test_buy_into_existing_portfolio(tlv: Instrument) -> None:
    repository = InMemoryPortfolioRepository()
    repository.save(Portfolio(name="Retirement", base_currency=Currency.RON))

    use_case = BuyShares(repository)
    position = use_case.execute(
        "Retirement", tlv, Decimal("100"), Money(amount=Decimal("4"), currency=Currency.RON)
    )

    assert position.quantity == Decimal("100")
    stored = repository.get("Retirement")
    assert stored is not None
    assert stored.get_position("TLV") is not None


def test_buy_into_missing_portfolio_raises(tlv: Instrument) -> None:
    repository = InMemoryPortfolioRepository()
    use_case = BuyShares(repository)

    with pytest.raises(PortfolioNotFoundError):
        use_case.execute(
            "Nonexistent", tlv, Decimal("10"), Money(amount=Decimal("4"), currency=Currency.RON)
        )


def test_currency_mismatch_propagates(tlv: Instrument) -> None:
    repository = InMemoryPortfolioRepository()
    repository.save(Portfolio(name="Retirement", base_currency=Currency.RON))
    use_case = BuyShares(repository)

    with pytest.raises(CurrencyMismatchError):
        use_case.execute(
            "Retirement", tlv, Decimal("10"), Money(amount=Decimal("4"), currency=Currency.USD)
        )
