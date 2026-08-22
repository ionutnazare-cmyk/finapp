"""The ``Instrument`` entity: a tradeable security listed on an exchange."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from finapp.domain.value_objects.enums import AssetType, Currency


class Instrument(BaseModel):
    """A tradeable security, e.g. a BVB-listed equity such as TLV or SNP.

    Instruments are identified by their ``symbol`` and are immutable: if an
    instrument's static metadata changes (rare — a name change, a currency
    redenomination), a new :class:`Instrument` should be constructed rather
    than mutating an existing one.
    """

    model_config = ConfigDict(frozen=True)

    symbol: str = Field(min_length=1, max_length=16)
    name: str = Field(min_length=1)
    currency: Currency
    asset_type: AssetType
    exchange: str = Field(default="BVB", min_length=1)
    isin: str | None = Field(default=None, min_length=12, max_length=12)

    @field_validator("symbol")
    @classmethod
    def _symbol_uppercase(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("Instrument.symbol must not be blank")
        return normalized

    @field_validator("isin")
    @classmethod
    def _isin_uppercase(cls, value: str | None) -> str | None:
        return value.strip().upper() if value else value

    def __str__(self) -> str:
        return f"{self.symbol} ({self.exchange})"
