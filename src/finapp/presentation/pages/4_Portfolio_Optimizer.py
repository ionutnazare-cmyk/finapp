"""Portfolio Optimizer page.

Wraps the Sprint 1.10 mean-variance optimizer. Unlike the other new pages,
this one needs no stored portfolio — its inputs (expected returns,
volatilities) are assumptions you supply directly, since there's no
historical-return data source yet (that arrives with automatic BVB data
updates, a later sprint).

To keep the input UI simple, the full covariance matrix isn't entered
directly: you provide each asset's volatility plus a single assumed
pairwise correlation applied between every pair. This is a simplification
(real assets have their own pairwise correlations), not a limitation of
the underlying optimizer, which accepts a full matrix.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

import pandas as pd
import streamlit as st

from finapp.application.use_cases.optimize_portfolio import (
    OptimizationObjective,
    OptimizePortfolio,
)
from finapp.domain.exceptions import DomainError, OptimizationFailedError
from finapp.domain.services.portfolio_optimizer import OptimizationInput

st.set_page_config(page_title="Portfolio Optimizer — FinApp", page_icon="📐", layout="wide")


def _to_decimal(raw: float, field_label: str) -> Decimal | None:
    try:
        return Decimal(str(raw))
    except InvalidOperation:
        st.error(f"'{field_label}' is not a valid number.")
        return None


def render() -> None:
    st.title("Portfolio Optimizer 📐")
    st.caption(
        "Mean-variance optimization (Markowitz): finds long-only, fully-invested "
        "weights that either maximize risk-adjusted return (Sharpe ratio) or "
        "minimize volatility. Enter your own return/volatility assumptions below — "
        "this isn't tied to a stored portfolio."
    )

    st.subheader("Assets")
    default_rows = pd.DataFrame(
        [
            {"Symbol": "TLV", "Expected return (%)": 8.0, "Volatility (%)": 22.0},
            {"Symbol": "SNP", "Expected return (%)": 6.0, "Volatility (%)": 18.0},
        ]
    )
    rows = st.data_editor(default_rows, num_rows="dynamic", use_container_width=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        correlation = st.slider(
            "Assumed pairwise correlation between every pair of assets",
            min_value=-1.0,
            max_value=1.0,
            value=0.3,
            step=0.05,
        )
    with col2:
        risk_free_rate = st.number_input("Risk-free rate (%)", value=3.0, step=0.25, format="%.2f")
    with col3:
        objective = st.selectbox(
            "Objective",
            [OptimizationObjective.MAXIMIZE_SHARPE_RATIO, OptimizationObjective.MINIMIZE_VOLATILITY],
            format_func=lambda o: "Maximize Sharpe ratio"
            if o == OptimizationObjective.MAXIMIZE_SHARPE_RATIO
            else "Minimize volatility",
        )

    target_return: float | None = None
    if objective == OptimizationObjective.MINIMIZE_VOLATILITY:
        set_target = st.checkbox("Constrain to a specific target return")
        if set_target:
            target_return = st.number_input("Target return (%)", value=7.0, step=0.5, format="%.2f")

    if not st.button("Optimize"):
        return

    symbols = [str(s).strip().upper() for s in rows["Symbol"] if str(s).strip()]
    if len(symbols) < 2:
        st.error("At least 2 assets are required to optimize a portfolio.")
        return
    if len(set(symbols)) != len(symbols):
        st.error("Symbols must be unique.")
        return

    expected_returns: list[Decimal] = []
    volatilities: list[Decimal] = []
    for _, row in rows.iterrows():
        symbol = str(row["Symbol"]).strip()
        if not symbol:
            continue
        expected_return = _to_decimal(float(row["Expected return (%)"]) / 100, f"{symbol} return")
        volatility = _to_decimal(float(row["Volatility (%)"]) / 100, f"{symbol} volatility")
        if expected_return is None or volatility is None:
            return
        expected_returns.append(expected_return)
        volatilities.append(volatility)

    correlation_decimal = _to_decimal(correlation, "Correlation")
    risk_free_rate_decimal = _to_decimal(risk_free_rate / 100, "Risk-free rate")
    if correlation_decimal is None or risk_free_rate_decimal is None:
        return

    n = len(symbols)
    covariance_matrix = tuple(
        tuple(
            volatilities[i] * volatilities[i]
            if i == j
            else correlation_decimal * volatilities[i] * volatilities[j]
            for j in range(n)
        )
        for i in range(n)
    )

    target_return_decimal = None
    if target_return is not None:
        target_return_decimal = _to_decimal(target_return / 100, "Target return")
        if target_return_decimal is None:
            return

    try:
        inputs = OptimizationInput(
            symbols=tuple(symbols),
            expected_returns=tuple(expected_returns),
            covariance_matrix=covariance_matrix,
            risk_free_rate=risk_free_rate_decimal,
        )
        result = OptimizePortfolio().execute(
            inputs, objective=objective, target_return=target_return_decimal
        )
    except OptimizationFailedError as exc:
        st.error(str(exc))
        return
    except DomainError as exc:
        st.error(str(exc))
        return
    except Exception as exc:  # noqa: BLE001 - surface pydantic validation errors too
        st.error(f"Invalid inputs: {exc}")
        return

    st.subheader("Optimal allocation")
    st.dataframe(
        pd.DataFrame(
            [{"Symbol": a.symbol, "Weight": f"{float(a.weight):.1%}"} for a in result.allocations]
        ),
        use_container_width=True,
        hide_index=True,
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Expected return", f"{float(result.expected_return):.2%}")
    col2.metric("Expected volatility", f"{float(result.expected_volatility):.2%}")
    col3.metric("Sharpe ratio", f"{float(result.sharpe_ratio):.2f}")


render()
