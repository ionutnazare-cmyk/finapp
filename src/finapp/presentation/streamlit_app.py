"""Streamlit entry point for FinApp."""

from typing import cast

import pandas as pd
import streamlit as st

from finapp.application.import_transactions import import_csv
from finapp.application.summary import build_summary
from finapp.infrastructure.repositories import InMemoryTransactionRepository


def _repository() -> InMemoryTransactionRepository:
    if "repository" not in st.session_state:
        st.session_state.repository = InMemoryTransactionRepository()
    return cast(InMemoryTransactionRepository, st.session_state["repository"])


def main() -> None:
    st.set_page_config(page_title="FinApp", page_icon="💰", layout="wide")
    st.title("FinApp")
    st.caption("Import transactions and understand where your money goes.")

    upload = st.file_uploader("Transaction CSV", type="csv")
    repository = _repository()
    if upload is not None and st.button("Import transactions", type="primary"):
        try:
            result = import_csv(upload.getvalue(), repository)
        except ValueError as error:
            st.error(str(error))
        else:
            st.success(f"Imported {result.imported_count} transaction(s).")
            for row_error in result.errors:
                st.warning(f"Row {row_error.row_number}: {row_error.message}")

    transactions = repository.list_all()
    summary = build_summary(transactions)
    income, expenses, balance = st.columns(3)
    income.metric("Income", f"{summary.income:,.2f}")
    expenses.metric("Expenses", f"{summary.expenses:,.2f}")
    balance.metric("Balance", f"{summary.balance:,.2f}")

    if summary.categories:
        st.subheader("Expense categories")
        chart_data = pd.DataFrame(item.model_dump() for item in summary.categories)
        st.bar_chart(chart_data, x="category", y="amount")

    if transactions:
        st.subheader("Transactions")
        transaction_data = pd.DataFrame(item.model_dump() for item in transactions)
        st.dataframe(transaction_data, use_container_width=True)


if __name__ == "__main__":
    main()
