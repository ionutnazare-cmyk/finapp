"""A :class:`PortfolioRepository` backed by local JSON files, one per portfolio."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any

from finapp.application.ports import PortfolioRepository
from finapp.domain.entities.instrument import Instrument
from finapp.domain.entities.portfolio import Portfolio
from finapp.domain.entities.position import Position
from finapp.domain.value_objects.enums import AssetType, Currency
from finapp.domain.value_objects.money import Money

_SAFE_NAME_PATTERN = re.compile(r"[^A-Za-z0-9_-]+")


def _slugify(name: str) -> str:
    slug = _SAFE_NAME_PATTERN.sub("_", name.strip())
    if not slug:
        raise ValueError(f"Portfolio name '{name}' has no valid filename characters")
    return slug


class JsonPortfolioRepository(PortfolioRepository):
    """Persists each portfolio as ``<directory>/<slugified-name>.json``.

    The JSON schema is FinApp's own normalized representation, not tied to
    any external format: portfolio name, base currency, and a list of
    positions with their instrument metadata, quantity, and average cost.
    Monetary amounts and quantities are stored as strings to preserve exact
    ``Decimal`` precision across a save/load round trip. Saves are written
    to a temporary file and then atomically renamed into place, so a save
    interrupted partway through never leaves a corrupt file behind.
    """

    def __init__(self, directory: Path) -> None:
        self._directory = directory
        self._directory.mkdir(parents=True, exist_ok=True)

    def _path_for(self, name: str) -> Path:
        return self._directory / f"{_slugify(name)}.json"

    def get(self, name: str) -> Portfolio | None:
        path = self._path_for(name)
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as handle:
            payload: dict[str, Any] = json.load(handle)
        return self._from_payload(payload)

    def save(self, portfolio: Portfolio) -> None:
        path = self._path_for(portfolio.name)
        payload = self._to_payload(portfolio)
        tmp_path = path.with_suffix(".json.tmp")
        with tmp_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
        os.replace(tmp_path, path)

    def list_names(self) -> Sequence[str]:
        names: list[str] = []
        for path in sorted(self._directory.glob("*.json")):
            with path.open("r", encoding="utf-8") as handle:
                payload: dict[str, Any] = json.load(handle)
            names.append(payload["name"])
        return tuple(names)

    @staticmethod
    def _to_payload(portfolio: Portfolio) -> dict[str, Any]:
        return {
            "name": portfolio.name,
            "base_currency": portfolio.base_currency.value,
            "positions": [
                {
                    "instrument": {
                        "symbol": position.instrument.symbol,
                        "name": position.instrument.name,
                        "currency": position.instrument.currency.value,
                        "asset_type": position.instrument.asset_type.value,
                        "exchange": position.instrument.exchange,
                        "isin": position.instrument.isin,
                    },
                    "quantity": str(position.quantity),
                    "average_cost": str(position.average_cost.amount),
                }
                for position in portfolio.positions.values()
            ],
        }

    @staticmethod
    def _from_payload(payload: dict[str, Any]) -> Portfolio:
        base_currency = Currency(payload["base_currency"])
        positions: list[Position] = []
        for raw_position in payload["positions"]:
            raw_instrument = raw_position["instrument"]
            instrument = Instrument(
                symbol=raw_instrument["symbol"],
                name=raw_instrument["name"],
                currency=Currency(raw_instrument["currency"]),
                asset_type=AssetType(raw_instrument["asset_type"]),
                exchange=raw_instrument["exchange"],
                isin=raw_instrument["isin"],
            )
            positions.append(
                Position(
                    instrument=instrument,
                    quantity=Decimal(raw_position["quantity"]),
                    average_cost=Money(
                        amount=Decimal(raw_position["average_cost"]),
                        currency=instrument.currency,
                    ),
                )
            )
        return Portfolio(name=payload["name"], base_currency=base_currency, positions=positions)
