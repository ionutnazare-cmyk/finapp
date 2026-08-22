from __future__ import annotations

from decimal import Decimal

import pytest

from finapp.domain.entities.instrument import Instrument
from finapp.domain.entities.portfolio import Portfolio
from finapp.domain.exceptions import (
    CurrencyMismatchError,
    InsufficientSharesError,
    UnknownInstrumentError,
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


@pytest.fixture
def snp() -> Instrument:
    return Instrument(
        symbol="SNP",
        name="OMV Petrom",
        currency=Currency.RON,
        asset_type=AssetType.EQUITY,
    )


@pytest.fixture
def portfolio() -> Portfolio:
    return Portfolio(name="Retirement", base_currency=Currency.RON)


def test_new_portfolio_is_empty(portfolio: Portfolio) -> None:
    assert portfolio.is_empty()
    assert len(portfolio) == 0


def test_buy_creates_position(portfolio: Portfolio, tlv: Instrument) -> None:
    position = portfolio.buy(tlv, Decimal("100"), Money(amount=Decimal("4"), currency=Currency.RON))
    assert position.quantity == Decimal("100")
    assert "TLV" in portfolio
    assert portfolio.get_position("TLV") is position


def test_buy_merges_into_existing_position(portfolio: Portfolio, tlv: Instrument) -> None:
    portfolio.buy(tlv, Decimal("100"), Money(amount=Decimal("4"), currency=Currency.RON))
    updated = portfolio.buy(tlv, Decimal("100"), Money(amount=Decimal("6"), currency=Currency.RON))
    assert updated.quantity == Decimal("200")
    assert updated.average_cost == Money(amount=Decimal("5"), currency=Currency.RON)
    assert len(portfolio) == 1


def test_sell_reduces_position(portfolio: Portfolio, tlv: Instrument) -> None:
    portfolio.buy(tlv, Decimal("100"), Money(amount=Decimal("4"), currency=Currency.RON))
    remaining = portfolio.sell("TLV", Decimal("40"))
    assert remaining is not None
    assert remaining.quantity == Decimal("60")


def test_sell_full_quantity_removes_position(portfolio: Portfolio, tlv: Instrument) -> None:
    portfolio.buy(tlv, Decimal("100"), Money(amount=Decimal("4"), currency=Currency.RON))
    result = portfolio.sell("TLV", Decimal("100"))
    assert result is None
    assert "TLV" not in portfolio
    assert portfolio.is_empty()


def test_sell_unknown_symbol_raises(portfolio: Portfolio) -> None:
    with pytest.raises(UnknownInstrumentError):
        portfolio.sell("UNKNOWN", Decimal("1"))


def test_sell_more_than_held_raises(portfolio: Portfolio, tlv: Instrument) -> None:
    portfolio.buy(tlv, Decimal("10"), Money(amount=Decimal("4"), currency=Currency.RON))
    with pytest.raises(InsufficientSharesError):
        portfolio.sell("TLV", Decimal("11"))


def test_total_book_cost_sums_positions(
    portfolio: Portfolio, tlv: Instrument, snp: Instrument
) -> None:
    portfolio.buy(tlv, Decimal("100"), Money(amount=Decimal("4"), currency=Currency.RON))
    portfolio.buy(snp, Decimal("1000"), Money(amount=Decimal("0.50"), currency=Currency.RON))
    assert portfolio.total_book_cost() == Money(amount=Decimal("900"), currency=Currency.RON)


def test_total_market_value_uses_supplied_prices(
    portfolio: Portfolio, tlv: Instrument, snp: Instrument
) -> None:
    portfolio.buy(tlv, Decimal("100"), Money(amount=Decimal("4"), currency=Currency.RON))
    portfolio.buy(snp, Decimal("1000"), Money(amount=Decimal("0.50"), currency=Currency.RON))
    prices = {
        "TLV": Money(amount=Decimal("4.50"), currency=Currency.RON),
        "SNP": Money(amount=Decimal("0.60"), currency=Currency.RON),
    }
    assert portfolio.total_market_value(prices) == Money(amount=Decimal("1050"), currency=Currency.RON)


def test_total_market_value_missing_price_raises(portfolio: Portfolio, tlv: Instrument) -> None:
    portfolio.buy(tlv, Decimal("100"), Money(amount=Decimal("4"), currency=Currency.RON))
    with pytest.raises(UnknownInstrumentError):
        portfolio.total_market_value({})


def test_buy_currency_mismatch_raises(portfolio: Portfolio, tlv: Instrument) -> None:
    with pytest.raises(CurrencyMismatchError):
        portfolio.buy(tlv, Decimal("10"), Money(amount=Decimal("4"), currency=Currency.USD))


def test_positions_view_is_read_only(portfolio: Portfolio, tlv: Instrument) -> None:
    portfolio.buy(tlv, Decimal("10"), Money(amount=Decimal("4"), currency=Currency.RON))
    with pytest.raises(TypeError):
        portfolio.positions["TLV"] = None  # type: ignore[index]


def test_blank_name_rejected() -> None:
    with pytest.raises(ValueError):
        Portfolio(name="   ", base_currency=Currency.RON)
