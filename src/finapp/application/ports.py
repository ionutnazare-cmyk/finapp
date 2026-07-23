"""Interfaces implemented by the infrastructure layer."""

from collections.abc import Iterable
from datetime import date
from decimal import Decimal
from typing import Protocol

from finapp.domain.entities import Transaction


class TransactionRepository(Protocol):
    """Persistence boundary for transactions."""

    def add_many(self, transactions: Iterable[Transaction]) -> None: ...

    def list_all(self) -> list[Transaction]: ...


class MarketDataProvider(Protocol):
    """Boundary for historical market-price data."""

    def get_price(self, ticker: str, on_date: date) -> Decimal: ...
