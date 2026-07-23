"""Domain entities independent of storage and UI concerns."""

from datetime import date
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TransactionKind(StrEnum):
    """Direction of money movement."""

    INCOME = "income"
    EXPENSE = "expense"


class Transaction(BaseModel):
    """A validated, categorised personal-finance transaction."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    id: UUID = Field(default_factory=uuid4)
    occurred_on: date
    description: str = Field(min_length=1, max_length=250)
    amount: Decimal = Field(max_digits=14, decimal_places=2)
    category: str = Field(default="Uncategorised", min_length=1, max_length=80)

    @field_validator("amount")
    @classmethod
    def amount_must_not_be_zero(cls, value: Decimal) -> Decimal:
        if value == 0:
            raise ValueError("amount must not be zero")
        return value.quantize(Decimal("0.01"))

    @property
    def kind(self) -> TransactionKind:
        return TransactionKind.INCOME if self.amount > 0 else TransactionKind.EXPENSE
