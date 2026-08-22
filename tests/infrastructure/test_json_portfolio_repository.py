from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from finapp.domain.entities.instrument import Instrument
from finapp.domain.entities.portfolio import Portfolio
from finapp.domain.value_objects.enums import AssetType, Currency
from finapp.domain.value_objects.money import Money
from finapp.infrastructure.repositories.json_portfolio_repository import (
    JsonPortfolioRepository,
)


def test_save_creates_json_file(tmp_path: Path) -> None:
    repository = JsonPortfolioRepository(tmp_path)
    portfolio = Portfolio(name="Retirement", base_currency=Currency.RON)

    repository.save(portfolio)

    assert (tmp_path / "Retirement.json").exists()


def test_round_trip_preserves_positions(tmp_path: Path) -> None:
    tlv = Instrument(
        symbol="TLV",
        name="Banca Transilvania",
        currency=Currency.RON,
        asset_type=AssetType.EQUITY,
        isin="ROU0698U1X08",
    )
    portfolio = Portfolio(name="Retirement", base_currency=Currency.RON)
    portfolio.buy(tlv, Decimal("100.5"), Money(amount=Decimal("4.1234"), currency=Currency.RON))

    repository = JsonPortfolioRepository(tmp_path)
    repository.save(portfolio)

    reloaded = repository.get("Retirement")
    assert reloaded is not None
    assert reloaded.name == "Retirement"
    assert reloaded.base_currency == Currency.RON

    position = reloaded.get_position("TLV")
    assert position is not None
    assert position.quantity == Decimal("100.5")
    assert position.average_cost == Money(amount=Decimal("4.1234"), currency=Currency.RON)
    assert position.instrument.isin == "ROU0698U1X08"


def test_get_missing_returns_none(tmp_path: Path) -> None:
    repository = JsonPortfolioRepository(tmp_path)
    assert repository.get("Nonexistent") is None


def test_list_names_reads_actual_portfolio_names(tmp_path: Path) -> None:
    repository = JsonPortfolioRepository(tmp_path)
    repository.save(Portfolio(name="Zeta Fund", base_currency=Currency.RON))
    repository.save(Portfolio(name="Alpha Fund", base_currency=Currency.RON))

    assert set(repository.list_names()) == {"Zeta Fund", "Alpha Fund"}


def test_save_is_atomic_no_tmp_file_left_behind(tmp_path: Path) -> None:
    repository = JsonPortfolioRepository(tmp_path)
    repository.save(Portfolio(name="Retirement", base_currency=Currency.RON))

    leftovers = list(tmp_path.glob("*.tmp"))
    assert leftovers == []


def test_name_with_spaces_is_slugified_to_a_valid_filename(tmp_path: Path) -> None:
    repository = JsonPortfolioRepository(tmp_path)
    repository.save(Portfolio(name="My Retirement Fund", base_currency=Currency.RON))

    assert (tmp_path / "My_Retirement_Fund.json").exists()
    assert repository.get("My Retirement Fund") is not None
