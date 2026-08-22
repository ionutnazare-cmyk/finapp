from __future__ import annotations

from decimal import Decimal

import pytest

from finapp.domain.entities.instrument import Instrument
from finapp.domain.entities.position import Position
from finapp.domain.exceptions import (
    CurrencyMismatchError,
    InsufficientSharesError,
    InvalidQuantityError,
)
from finapp.domain.value_objects.enums import AssetType, Currency
from finapp.domain.value_objects.money import Money


@pytest.fixture
def tlv() -> Instrument:
    return Instrument(
        symbol="TLV",
        name="Banca Transilvania",
        currency=Currency.RON,
        asset_type=AssetType.EQUITY,
    )


def test_book_cost(tlv: Instrument) -> None:
    position = Position(
        instrument=tlv,
        quantity=Decimal("100"),
        average_cost=Money(amount=Decimal("4.00"), currency=Currency.RON),
    )
    assert position.book_cost() == Money(amount=Decimal("400.00"), currency=Currency.RON)


def test_market_value_and_unrealized_pnl(tlv: Instrument) -> None:
    position = Position(
        instrument=tlv,
        quantity=Decimal("100"),
        average_cost=Money(amount=Decimal("4.00"), currency=Currency.RON),
    )
    price = Money(amount=Decimal("4.50"), currency=Currency.RON)
    assert position.market_value(price) == Money(amount=Decimal("450.00"), currency=Currency.RON)
    assert position.unrealized_pnl(price) == Money(amount=Decimal("50.00"), currency=Currency.RON)


def test_average_cost_currency_mismatch_rejected(tlv: Instrument) -> None:
    with pytest.raises(CurrencyMismatchError):
        Position(
            instrument=tlv,
            quantity=Decimal("10"),
            average_cost=Money(amount=Decimal("4.00"), currency=Currency.USD),
        )


def test_with_additional_shares_recomputes_weighted_average(tlv: Instrument) -> None:
    position = Position(
        instrument=tlv,
        quantity=Decimal("100"),
        average_cost=Money(amount=Decimal("4.00"), currency=Currency.RON),
    )
    updated = position.with_additional_shares(
        Decimal("100"), Money(amount=Decimal("6.00"), currency=Currency.RON)
    )
    assert updated.quantity == Decimal("200")
    assert updated.average_cost == Money(amount=Decimal("5.00"), currency=Currency.RON)
    # Original position is untouched (immutability).
    assert position.quantity == Decimal("100")


def test_with_reduced_shares_keeps_average_cost(tlv: Instrument) -> None:
    position = Position(
        instrument=tlv,
        quantity=Decimal("100"),
        average_cost=Money(amount=Decimal("4.00"), currency=Currency.RON),
    )
    updated = position.with_reduced_shares(Decimal("40"))
    assert updated.quantity == Decimal("60")
    assert updated.average_cost == position.average_cost


def test_with_reduced_shares_to_zero_marks_closed(tlv: Instrument) -> None:
    position = Position(
        instrument=tlv,
        quantity=Decimal("50"),
        average_cost=Money(amount=Decimal("4.00"), currency=Currency.RON),
    )
    updated = position.with_reduced_shares(Decimal("50"))
    assert updated.quantity == Decimal("0")
    assert updated.is_closed()


def test_cannot_reduce_more_shares_than_held(tlv: Instrument) -> None:
    position = Position(
        instrument=tlv,
        quantity=Decimal("10"),
        average_cost=Money(amount=Decimal("4.00"), currency=Currency.RON),
    )
    with pytest.raises(InsufficientSharesError):
        position.with_reduced_shares(Decimal("11"))


def test_cannot_add_non_positive_shares(tlv: Instrument) -> None:
    position = Position(
        instrument=tlv,
        quantity=Decimal("10"),
        average_cost=Money(amount=Decimal("4.00"), currency=Currency.RON),
    )
    with pytest.raises(InvalidQuantityError):
        position.with_additional_shares(
            Decimal("0"), Money(amount=Decimal("4.00"), currency=Currency.RON)
        )


def test_negative_initial_quantity_rejected(tlv: Instrument) -> None:
    with pytest.raises(InvalidQuantityError):
        Position(
            instrument=tlv,
            quantity=Decimal("-1"),
            average_cost=Money(amount=Decimal("4.00"), currency=Currency.RON),
        )
