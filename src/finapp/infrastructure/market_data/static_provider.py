"""An in-memory :class:`MarketDataProvider` backed by a fixed mapping of quotes."""

from __future__ import annotations

from collections.abc import Mapping

from finapp.application.dto import Quote
from finapp.application.exceptions import QuoteNotFoundError
from finapp.application.ports import MarketDataProvider


class StaticMarketDataProvider(MarketDataProvider):
    """A :class:`MarketDataProvider` backed by an in-memory mapping of quotes.

    Useful for unit tests, demos, and manual price overrides before a live
    BVB feed is wired in (see :class:`CsvMarketDataProvider` for a
    file-backed alternative, and the roadmap's automatic-update sprint for
    a future live adapter).
    """

    def __init__(self, quotes: Mapping[str, Quote]) -> None:
        self._quotes: dict[str, Quote] = {
            symbol.strip().upper(): quote for symbol, quote in quotes.items()
        }

    def get_quote(self, symbol: str) -> Quote:
        normalized = symbol.strip().upper()
        try:
            return self._quotes[normalized]
        except KeyError:
            raise QuoteNotFoundError(normalized) from None
