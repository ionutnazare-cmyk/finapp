"""Application-level exceptions.

Distinct from :mod:`finapp.domain.exceptions`: these represent failures in
orchestration or in a port's ability to fulfil a request (e.g. no data
available), not violations of core business invariants.
"""

from __future__ import annotations


class ApplicationError(Exception):
    """Base class for all application-layer errors."""


class QuoteNotFoundError(ApplicationError):
    """Raised when a :class:`~finapp.application.ports.MarketDataProvider`
    has no quote available for the requested symbol."""

    def __init__(self, symbol: str) -> None:
        super().__init__(f"No quote available for symbol '{symbol}'")
        self.symbol = symbol
