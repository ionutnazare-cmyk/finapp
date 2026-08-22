"""Domain-level exceptions.

All exceptions raised by domain entities and value objects derive from
:class:`DomainError`, so calling layers can catch domain violations
distinctly from infrastructure or presentation errors.
"""

from __future__ import annotations


class DomainError(Exception):
    """Base class for all domain-layer errors."""


class CurrencyMismatchError(DomainError):
    """Raised when an operation combines :class:`Money` of different currencies."""

    def __init__(self, expected: str, actual: str) -> None:
        super().__init__(f"Currency mismatch: expected {expected}, got {actual}")
        self.expected = expected
        self.actual = actual


class InvalidQuantityError(DomainError):
    """Raised when a share/unit quantity is invalid (e.g. negative or zero when
    a positive quantity is required)."""


class InsufficientSharesError(DomainError):
    """Raised when attempting to sell/remove more shares than a position holds."""

    def __init__(self, symbol: str, held: object, requested: object) -> None:
        super().__init__(
            f"Cannot remove {requested} shares of {symbol}: only {held} held"
        )
        self.symbol = symbol
        self.held = held
        self.requested = requested


class UnknownInstrumentError(DomainError):
    """Raised when a portfolio operation references a symbol it has no position for."""

    def __init__(self, symbol: str) -> None:
        super().__init__(f"No position found for symbol '{symbol}'")
        self.symbol = symbol
