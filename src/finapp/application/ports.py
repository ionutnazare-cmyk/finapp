"""Application ports: abstract interfaces implemented by the infrastructure layer.

Ports let use cases and the presentation layer depend on an abstraction
(e.g. "something that can provide quotes") rather than a concrete adapter
(e.g. "a CSV file" or "the BVB website"), so the concrete implementation can
change — or be swapped for a test double — without touching calling code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

from finapp.application.dto import PortfolioReport, Quote
from finapp.domain.entities.portfolio import Portfolio
from finapp.domain.value_objects.bonus_issue import BonusIssue
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


class BonusIssueProvider(ABC):
    """Port for retrieving known bonus share issues for instruments.

    TLV (Banca Transilvania) is BVB's most prominent example, having issued
    bonus shares in most recent years, but this port is generic — any
    instrument can have a bonus issue history. Mirrors
    :class:`DividendProvider`'s shape for consistency.
    """

    @abstractmethod
    def get_bonus_issues(self, symbol: str) -> Sequence[BonusIssue]:
        """Return all known :class:`BonusIssue` events for ``symbol``.

        Returns an empty sequence if the instrument has no known bonus issue
        history rather than raising — most instruments never issue bonus
        shares, and that's expected, not a failure.
        """

        raise NotImplementedError

    def get_latest_bonus_issue(self, symbol: str) -> BonusIssue | None:
        """Return the most recent known bonus issue for ``symbol``, or ``None``.

        The default implementation assumes :meth:`get_bonus_issues` returns
        events in chronological order and takes the last one; adapters that
        don't naturally return sorted data should override this.
        """

        issues = self.get_bonus_issues(symbol)
        return issues[-1] if issues else None


class PortfolioReportExporter(ABC):
    """Port for rendering a :class:`~finapp.application.dto.PortfolioReport`
    to a specific file format (Excel, PDF, ...).

    Infrastructure adapters implement this per format. There's exactly one
    concrete implementation per format for now, but the abstraction still
    earns its keep: it keeps ``openpyxl``/``reportlab`` out of the
    application and domain layers, and use cases depend only on "something
    that can export a report," not on a specific library.
    """

    @abstractmethod
    def export(self, report: PortfolioReport, output_path: Path) -> Path:
        """Render ``report`` and write it to ``output_path``, creating parent
        directories as needed. Returns the path actually written (normally
        just ``output_path`` unchanged)."""

        raise NotImplementedError
