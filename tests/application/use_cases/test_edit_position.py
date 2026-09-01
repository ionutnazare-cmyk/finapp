from __future__ import annotations

from decimal import Decimal

import pytest

from finapp.application.exceptions import PortfolioNotFoundError
from finapp.application.use_cases.edit_position import EditPosition
from finapp.domain.entities.instrument import Instrument
from finapp.domain.entities.portfolio import Portfolio
from finapp.domain.exceptions import InvalidQuantityError, UnknownInstrumentError
from finapp.domain.value_objects.enums import AssetType, Currency
from finapp.domain.value_objects.money import Money
from finapp.infrastructure.repositories.in_memory_portfolio_repository import (
    InMemoryPortfolioRepository,
)


@pytest.fixture
def repository_with_tlv_position() -> InMemoryPortfolioRepository:
    tlv = Instrument(
        symbol="TLV", name="Banca Transilvania", currency=Currency.RON, asset_type=AssetType.EQUITY
    )
    portfolio = Portfolio(name="Retirement", base_currency=Currency.RON)
    portfolio.buy(tlv, Decimal("100"), Money(amount=Decimal("4"), currency=Currency.RON))
    repository = InMemoryPortfolioRepository()
    repository.save(portfolio)
    return repository


def test_corrects_quantity_and_cost(
    repository_with_tlv_position: InMemoryPortfolioRepository,
) -> None:
    use_case = EditPosition(repository_with_tlv_position)

    result = use_case.execute(
        "Retirement", "TLV", Decimal("150"), Money(amount=Decimal("3.50"), currency=Currency.RON)
    )

    assert result is not None
    assert result.quantity == Decimal("150")
    stored = repository_with_tlv_position.get("Retirement")
    assert stored is not None
    position = stored.get_position("TLV")
    assert position is not None
    assert position.average_cost == Money(amount=Decimal("3.50"), currency=Currency.RON)


def test_setting_zero_removes_position(
    repository_with_tlv_position: InMemoryPortfolioRepository,
) -> None:
    use_case = EditPosition(repository_with_tlv_position)

    result = use_case.execute(
        "Retirement", "TLV", Decimal("0"), Money(amount=Decimal("4"), currency=Currency.RON)
    )

    assert result is None
    stored = repository_with_tlv_position.get("Retirement")
    assert stored is not None
    assert "TLV" not in stored


def test_missing_portfolio_raises() -> None:
    use_case = EditPosition(InMemoryPortfolioRepository())
    with pytest.raises(PortfolioNotFoundError):
        use_case.execute(
            "Nonexistent", "TLV", Decimal("100"), Money(amount=Decimal("4"), currency=Currency.RON)
        )


def test_unknown_symbol_raises(repository_with_tlv_position: InMemoryPortfolioRepository) -> None:
    use_case = EditPosition(repository_with_tlv_position)
    with pytest.raises(UnknownInstrumentError):
        use_case.execute(
            "Retirement", "SNP", Decimal("10"), Money(amount=Decimal("4"), currency=Currency.RON)
        )


def test_negative_quantity_raises(
    repository_with_tlv_position: InMemoryPortfolioRepository,
) -> None:
    use_case = EditPosition(repository_with_tlv_position)
    with pytest.raises(InvalidQuantityError):
        use_case.execute(
            "Retirement", "TLV", Decimal("-5"), Money(amount=Decimal("4"), currency=Currency.RON)
        )
