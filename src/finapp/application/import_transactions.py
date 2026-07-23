"""CSV import use case."""

from __future__ import annotations

from io import BytesIO

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from finapp.application.ports import TransactionRepository
from finapp.domain.entities import Transaction

REQUIRED_COLUMNS = frozenset({"date", "description", "amount"})


class RowImportError(BaseModel):
    """A source row rejected during an otherwise valid import."""

    model_config = ConfigDict(frozen=True)

    row_number: int = Field(ge=2)
    message: str


class ImportResult(BaseModel):
    """Result of a transaction import."""

    model_config = ConfigDict(frozen=True)

    imported_count: int
    errors: tuple[RowImportError, ...] = ()


def import_csv(content: bytes, repository: TransactionRepository) -> ImportResult:
    """Parse and persist valid records from a standard FinApp CSV file."""
    frame = pd.read_csv(BytesIO(content))
    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        required = ", ".join(sorted(missing))
        raise ValueError(f"CSV is missing required column(s): {required}")

    transactions: list[Transaction] = []
    errors: list[RowImportError] = []
    for position, row in frame.iterrows():
        try:
            transactions.append(_to_transaction(row))
        except (ValidationError, TypeError, ValueError) as error:
            errors.append(RowImportError(row_number=position + 2, message=str(error)))

    repository.add_many(transactions)
    return ImportResult(imported_count=len(transactions), errors=tuple(errors))


def _to_transaction(row: pd.Series[object]) -> Transaction:
    category = row.get("category", "Uncategorised")
    resolved_category = "Uncategorised" if pd.isna(category) else str(category)
    return Transaction(
        occurred_on=pd.to_datetime(row["date"], errors="raise").date(),
        description=str(row["description"]),
        amount=str(row["amount"]),
        category=resolved_category,
    )
