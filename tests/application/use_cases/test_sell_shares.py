from __future__ import annotations

from decimal import Decimal

import pytest

from finapp.application.exceptions import PortfolioNotFoundError
from finapp.application.use_cases.sell_shares import SellShares
from finapp.domain.entities.instrument import Instrument
from finapp.domain.entities.portfolio import Portfolio
from finapp.domain.exceptions import InsufficientSharesError, UnknownInstrumentError
from finapp.domain.value_objects.enums import AssetType, Currency
from finapp.domain.value_objects.money import Money
from finapp.infrastructure.repositories.in_memory_portfolio_repository import (
    InMemoryPortfolioRepository,
)


@pytest.fixture
def repository_with_tlv_position() -> InMemoryPortfolioRepository:
    tlv = Instrument(
        symbol="TLV",
        name="Banca Transilvania",
        currency=Currency.RON,
        asset_type=AssetType.EQUITY,
    )
    portfolio = Portfolio(name="Retirement", base_currency=Currency.RON)
    portfolio.buy(tlv, Decimal("100"), Money(amount=Decimal("4"), currency=Currency.RON))
    repository = InMemoryPortfolioRepository()
    repository.save(portfolio)
    return repository


def test_partial_sell_reduces_position(
    repository_with_tlv_position: InMemoryPortfolioRepository,
) -> None:
    use_case = SellShares(repository_with_tlv_position)
    result = use_case.execute("Retirement", "TLV", Decimal("40"))

    assert result is not None
    assert result.quantity == Decimal("60")
    stored = repository_with_tlv_position.get("Retirement")
    assert stored is not None
    assert stored.get_position("TLV").quantity == Decimal("60")  # type: ignore[union-attr]


def test_full_sell_closes_position(
    repository_with_tlv_position: InMemoryPortfolioRepository,
) -> None:
    use_case = SellShares(repository_with_tlv_position)
    result = use_case.execute("Retirement", "TLV", Decimal("100"))

    assert result is None
    stored = repository_with_tlv_position.get("Retirement")
    assert stored is not None
    assert "TLV" not in stored


def test_sell_from_missing_portfolio_raises() -> None:
    repository = InMemoryPortfolioRepository()
    use_case = SellShares(repository)

    with pytest.raises(PortfolioNotFoundError):
        use_case.execute("Nonexistent", "TLV", Decimal("1"))


def test_sell_unknown_symbol_raises(
    repository_with_tlv_position: InMemoryPortfolioRepository,
) -> None:
    use_case = SellShares(repository_with_tlv_position)
    with pytest.raises(UnknownInstrumentError):
        use_case.execute("Retirement", "SNP", Decimal("1"))


def test_sell_more_than_held_raises(
    repository_with_tlv_position: InMemoryPortfolioRepository,
) -> None:
    use_case = SellShares(repository_with_tlv_position)
    with pytest.raises(InsufficientSharesError):
        use_case.execute("Retirement", "TLV", Decimal("101"))
