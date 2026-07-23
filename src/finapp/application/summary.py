"""Financial summary use case."""

from decimal import Decimal

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict

from finapp.domain.entities import Transaction


class CategoryTotal(BaseModel):
    model_config = ConfigDict(frozen=True)

    category: str
    amount: Decimal
    share_percent: float


class FinancialSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    income: Decimal
    expenses: Decimal
    balance: Decimal
    categories: tuple[CategoryTotal, ...]


def build_summary(transactions: list[Transaction]) -> FinancialSummary:
    """Calculate balance and expense category allocation from transactions."""
    if not transactions:
        return FinancialSummary(
            income=Decimal("0.00"),
            expenses=Decimal("0.00"),
            balance=Decimal("0.00"),
            categories=(),
        )

    rows = [
        {"category": item.category, "amount": float(item.amount)}
        for item in transactions
    ]
    frame = pd.DataFrame(rows)
    income = Decimal(str(frame.loc[frame["amount"] > 0, "amount"].sum())).quantize(
        Decimal("0.01")
    )
    expenses = Decimal(str(frame.loc[frame["amount"] < 0, "amount"].sum())).quantize(
        Decimal("0.01")
    )
    expense_frame = frame.loc[frame["amount"] < 0].copy()
    grouped = expense_frame.groupby("category", as_index=False)["amount"].sum()
    grouped["amount"] = grouped["amount"].abs()
    total_expenses = float(grouped["amount"].sum())
    grouped["share_percent"] = np.where(
        total_expenses > 0,
        grouped["amount"] / total_expenses * 100,
        0.0,
    )
    categories = tuple(
        CategoryTotal(
            category=str(row.category),
            amount=Decimal(str(row.amount)).quantize(Decimal("0.01")),
            share_percent=round(float(row.share_percent), 2),
        )
        for row in grouped.sort_values(
            "amount", ascending=False
        ).itertuples(index=False)
    )
    return FinancialSummary(
        income=income,
        expenses=expenses,
        balance=(income + expenses).quantize(Decimal("0.01")),
        categories=categories,
    )
