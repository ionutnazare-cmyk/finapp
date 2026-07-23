"""JSON-backed deterministic market-data adapter."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

type PriceSeries = dict[str, dict[str, Decimal]]


class StaticPriceProvider:
    """Read ticker prices from JSON keyed by ticker and ISO date."""

    def __init__(self, prices: PriceSeries) -> None:
        self._prices = {ticker.upper(): values for ticker, values in prices.items()}

    @classmethod
    def from_json(cls, path: Path) -> StaticPriceProvider:
        """Create a provider from ``{\"TLV\": {\"2026-01-01\": \"40\"}}`` JSON."""
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("price JSON root must be an object")
        prices: PriceSeries = {}
        for ticker, values in raw.items():
            if not isinstance(ticker, str) or not isinstance(values, dict):
                raise ValueError("each price entry must map a ticker to dated prices")
            prices[ticker] = {}
            for price_date, value in values.items():
                try:
                    price = Decimal(str(value))
                except (InvalidOperation, ValueError) as error:
                    message = f"invalid price for {ticker} on {price_date}"
                    raise ValueError(message) from error
                if price <= 0:
                    message = f"price for {ticker} on {price_date} must be positive"
                    raise ValueError(message)
                prices[ticker][price_date] = price
        return cls(prices)

    def get_price(self, ticker: str, on_date: date) -> Decimal:
        """Return the exact configured price for a ticker at an investment date."""
        try:
            return self._prices[ticker.upper()][on_date.isoformat()]
        except KeyError as error:
            message = f"missing price for {ticker.upper()} on {on_date.isoformat()}"
            raise ValueError(message) from error
