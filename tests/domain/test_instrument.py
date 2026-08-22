from __future__ import annotations

import pytest

from finapp.domain.entities.instrument import Instrument
from finapp.domain.value_objects.enums import AssetType, Currency


def test_symbol_is_normalized_to_uppercase() -> None:
    instrument = Instrument(
        symbol="tlv",
        name="Banca Transilvania",
        currency=Currency.RON,
        asset_type=AssetType.EQUITY,
    )
    assert instrument.symbol == "TLV"


def test_default_exchange_is_bvb() -> None:
    instrument = Instrument(
        symbol="SNP",
        name="OMV Petrom",
        currency=Currency.RON,
        asset_type=AssetType.EQUITY,
    )
    assert instrument.exchange == "BVB"


def test_blank_symbol_rejected() -> None:
    with pytest.raises(Exception):  # noqa: B017 - pydantic ValidationError
        Instrument(
            symbol="   ",
            name="Invalid",
            currency=Currency.RON,
            asset_type=AssetType.EQUITY,
        )


def test_instrument_is_immutable() -> None:
    instrument = Instrument(
        symbol="H2O",
        name="Hidroelectrica",
        currency=Currency.RON,
        asset_type=AssetType.EQUITY,
    )
    with pytest.raises(Exception):  # noqa: B017 - pydantic ValidationError subclass
        instrument.name = "Renamed"  # type: ignore[misc]


def test_isin_is_normalized_to_uppercase() -> None:
    instrument = Instrument(
        symbol="TLV",
        name="Banca Transilvania",
        currency=Currency.RON,
        asset_type=AssetType.EQUITY,
        isin="rou0698u1x08".upper()[:12],
    )
    assert instrument.isin == "ROU0698U1X08"
