"""In-memory repository adapter used by the first sprint."""

from collections.abc import Iterable

from finapp.domain.entities import Transaction


class InMemoryTransactionRepository:
    """Simple process-local transaction store."""

    def __init__(self) -> None:
        self._transactions: list[Transaction] = []

    def add_many(self, transactions: Iterable[Transaction]) -> None:
        self._transactions.extend(transactions)

    def list_all(self) -> list[Transaction]:
        return list(self._transactions)
