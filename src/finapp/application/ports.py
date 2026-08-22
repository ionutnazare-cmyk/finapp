"""Application ports: abstract interfaces implemented by the infrastructure layer.

Ports let use cases and the presentation layer depend on an abstraction
(e.g. "something that can provide quotes") rather than a concrete adapter
(e.g. "a CSV file" or "the BVB website"), so the concrete implementation can
change — or be swapped for a test double — without touching calling code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping

from finapp.application.dto import Quote


class MarketDataProvider(ABC):
    """Port for retrieving current market quotes for instruments.

    Infrastructure adapters (a local CSV cache, a BVB scraper, a broker API)
    implement this interface. The application and presentation layers depend
    only on this abstraction, never on a concrete provider directly.
    """

    @abstractmethod
    def get_quote(self, symbol: str) -> Quote:
        """Return the latest known :class:`Quote` for ``symbol``.

        Raises :class:`~finapp.application.exceptions.QuoteNotFoundError` if
        no quote is available for the symbol.
        """

        raise NotImplementedError

    def get_quotes(self, symbols: Iterable[str]) -> Mapping[str, Quote]:
        """Return quotes for multiple symbols, keyed by (normalized) symbol.

        The default implementation calls :meth:`get_quote` once per symbol.
        Adapters that support genuine bulk retrieval (e.g. a single HTTP
        request covering many tickers) should override this method for
        efficiency; callers should not rely on call count, only on the
        returned mapping.
        """

        return {symbol: self.get_quote(symbol) for symbol in symbols}
