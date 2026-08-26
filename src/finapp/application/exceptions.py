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


class PortfolioNotFoundError(ApplicationError):
    """Raised when a use case references a portfolio that doesn't exist."""

    def __init__(self, name: str) -> None:
        super().__init__(f"No portfolio found named '{name}'")
        self.name = name


class PortfolioAlreadyExistsError(ApplicationError):
    """Raised when attempting to create a portfolio under a name already in use."""

    def __init__(self, name: str) -> None:
        super().__init__(f"A portfolio named '{name}' already exists")
        self.name = name


class InvalidAllocationError(ApplicationError):
    """Raised when a DCA target allocation is malformed: empty, containing a
    non-positive weight, or with weights that don't sum to 1."""


class InvalidFairValueRequestError(ApplicationError):
    """Raised when a fair value request is missing the inputs its chosen
    model needs (e.g. asking for Gordon Growth DDM without a growth rate)."""
