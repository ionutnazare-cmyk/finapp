"""Application ports: abstract interfaces implemented by the infrastructure layer.

Ports let use cases and the presentation layer depend on an abstraction
(e.g. "something that can provide quotes") rather than a concrete adapter
(e.g. "a CSV file" or "the BVB website"), so the concrete implementation can
change — or be swapped for a test double — without touching calling code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping, Sequence

from finapp.application.dto import Quote
from finapp.domain.entities.portfolio import Portfolio
from finapp.domain.value_objects.dividend import Dividend


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


class PortfolioRepository(ABC):
    """Port for loading and persisting :class:`Portfolio` aggregates.

    Infrastructure adapters (in-memory, a local JSON file cache, eventually
    a database) implement this interface. Use cases depend only on this
    abstraction, never on how or where portfolios are actually stored.
    """

    @abstractmethod
    def get(self, name: str) -> Portfolio | None:
        """Return the portfolio named ``name``, or ``None`` if it doesn't exist."""

        raise NotImplementedError

    @abstractmethod
    def save(self, portfolio: Portfolio) -> None:
        """Persist ``portfolio``, creating or overwriting it by name."""

        raise NotImplementedError

    @abstractmethod
    def list_names(self) -> Sequence[str]:
        """Return the names of all portfolios currently persisted."""

        raise NotImplementedError


class DividendProvider(ABC):
    """Port for retrieving known dividend payments for instruments.

    Infrastructure adapters (a local CSV cache, a BVB data source) implement
    this interface. Mirrors :class:`MarketDataProvider`'s shape so the two
    ports feel consistent to work with.
    """

    @abstractmethod
    def get_dividends(self, symbol: str) -> Sequence[Dividend]:
        """Return all known :class:`Dividend` payments for ``symbol``.

        Returns an empty sequence if the instrument has no known dividend
        history (e.g. it has never paid one) rather than raising — a missing
        dividend history is a normal, expected state, unlike a missing price
        quote.
        """

        raise NotImplementedError

    def get_latest_dividend(self, symbol: str) -> Dividend | None:
        """Return the most recent known dividend for ``symbol``, or ``None``.

        The default implementation assumes :meth:`get_dividends` returns
        payments in chronological order and takes the last one; adapters
        that don't naturally return sorted data should override this.
        """

        dividends = self.get_dividends(symbol)
        return dividends[-1] if dividends else None
