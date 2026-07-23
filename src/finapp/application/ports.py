"""Interfaces implemented by the infrastructure layer."""

from collections.abc import Iterable
from typing import Protocol

from finapp.domain.entities import Transaction


class TransactionRepository(Protocol):
    """Persistence boundary for transactions."""

    def add_many(self, transactions: Iterable[Transaction]) -> None: ...

    def list_all(self) -> list[Transaction]: ...
