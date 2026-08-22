"""Small, framework-independent enumerations shared across the domain layer."""

from __future__ import annotations

from enum import StrEnum


class Currency(StrEnum):
    """ISO 4217 currency codes supported by FinApp.

    RON is the primary currency (BVB is quoted in RON); others are included
    so foreign-listed instruments and reporting can be represented without
    a schema change.
    """

    RON = "RON"
    EUR = "EUR"
    USD = "USD"
    GBP = "GBP"


class AssetType(StrEnum):
    """Broad classification of a tradeable instrument."""

    EQUITY = "EQUITY"
    ETF = "ETF"
    BOND = "BOND"
    FUND = "FUND"
    CASH = "CASH"
