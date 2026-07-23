from datetime import date
from decimal import Decimal

from finapp.application.summary import build_summary
from finapp.domain.entities import Transaction


def test_summary_calculates_income_expenses_balance_and_categories() -> None:
    summary = build_summary(
        [
            Transaction(
                occurred_on=date(2026, 1, 1),
                description="Salary",
                amount=Decimal("3000"),
            ),
            Transaction(
                occurred_on=date(2026, 1, 2),
                description="Groceries",
                amount=Decimal("-120"),
                category="Food",
            ),
            Transaction(
                occurred_on=date(2026, 1, 3),
                description="Rent",
                amount=Decimal("-900"),
                category="Housing",
            ),
        ]
    )

    assert summary.income == Decimal("3000.00")
    assert summary.expenses == Decimal("-1020.00")
    assert summary.balance == Decimal("1980.00")
    assert summary.categories[0].category == "Housing"
    assert summary.categories[0].share_percent == 88.24


def test_empty_summary_is_zeroed() -> None:
    summary = build_summary([])

    assert summary.income == Decimal("0.00")
    assert summary.categories == ()
