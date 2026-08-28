"""Retirement Planning page.

Answers "will my money actually last through retirement" — a two-phase
simulation (accumulation, then withdrawals) from Sprint 1.11, starting from
the portfolio's current market value. Different question from Monte Carlo
(which only projects growth, with no withdrawal phase).
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

import pandas as pd
import streamlit as st

from finapp.application.exceptions import ApplicationError
from finapp.application.use_cases.run_portfolio_retirement_plan import (
    RunPortfolioRetirementPlan,
)
from finapp.domain.exceptions import DomainError
from finapp.domain.services.retirement_planning import RetirementPlanAssumptions
from finapp.presentation.streamlit_common import (
    get_market_data_provider,
    get_portfolio_repository,
    select_or_create_portfolio,
)

st.set_page_config(page_title="Retirement Planning — FinApp", page_icon="🏖️", layout="wide")


def _to_decimal(raw: float, field_label: str) -> Decimal | None:
    try:
        return Decimal(str(raw))
    except InvalidOperation:
        st.error(f"'{field_label}' is not a valid number.")
        return None


def render() -> None:
    st.title("Retirement Planning 🏖️")
    st.caption(
        "Simulates years of contributions followed by years of withdrawals, and "
        "reports the probability your portfolio is fully depleted before the end "
        "of retirement — starting from this portfolio's current market value."
    )

    portfolio = select_or_create_portfolio(key_prefix="retirement")
    if portfolio is None:
        st.info("Select or create a portfolio in the sidebar to get started.")
        return

    if portfolio.is_empty():
        st.info("This portfolio has no positions yet — buy something first on Portfolio Overview.")
        return

    currency_label = portfolio.base_currency.value

    st.subheader("Accumulation phase (before retirement)")
    col1, col2 = st.columns(2)
    with col1:
        accumulation_years = st.number_input(
            "Years until retirement", min_value=0, max_value=80, value=15, step=1
        )
        accumulation_return = st.number_input(
            "Expected annual return (%)", value=7.0, step=0.5, format="%.2f", key="acc_return"
        )
    with col2:
        accumulation_volatility = st.number_input(
            "Annual volatility (%)", min_value=0.0, value=15.0, step=0.5, format="%.2f", key="acc_vol"
        )
        annual_contribution = st.number_input(
            f"Annual contribution ({currency_label})", min_value=0.0, value=10000.0, step=500.0
        )

    st.subheader("Retirement phase (withdrawals)")
    col3, col4 = st.columns(2)
    with col3:
        retirement_years = st.number_input(
            "Years in retirement", min_value=1, max_value=80, value=25, step=1
        )
        retirement_return = st.number_input(
            "Expected annual return (%)", value=4.0, step=0.5, format="%.2f", key="ret_return"
        )
    with col4:
        retirement_volatility = st.number_input(
            "Annual volatility (%)", min_value=0.0, value=8.0, step=0.5, format="%.2f", key="ret_vol"
        )
        annual_withdrawal = st.number_input(
            f"Annual withdrawal ({currency_label})", min_value=0.0, value=40000.0, step=500.0
        )

    col5, col6 = st.columns(2)
    with col5:
        simulations = st.number_input(
            "Simulations", min_value=100, max_value=200_000, value=5000, step=100
        )
    with col6:
        use_seed = st.checkbox("Use a fixed random seed (reproducible results)", value=True)
        seed = st.number_input("Seed", value=42, step=1, disabled=not use_seed)

    if not st.button("Run retirement plan"):
        return

    accumulation_return_decimal = _to_decimal(accumulation_return / 100, "Expected return")
    accumulation_volatility_decimal = _to_decimal(accumulation_volatility / 100, "Volatility")
    annual_contribution_decimal = _to_decimal(annual_contribution, "Annual contribution")
    retirement_return_decimal = _to_decimal(retirement_return / 100, "Expected return")
    retirement_volatility_decimal = _to_decimal(retirement_volatility / 100, "Volatility")
    annual_withdrawal_decimal = _to_decimal(annual_withdrawal, "Annual withdrawal")
    if (
        accumulation_return_decimal is None
        or accumulation_volatility_decimal is None
        or annual_contribution_decimal is None
        or retirement_return_decimal is None
        or retirement_volatility_decimal is None
        or annual_withdrawal_decimal is None
    ):
        return

    try:
        assumptions = RetirementPlanAssumptions(
            accumulation_years=int(accumulation_years),
            accumulation_expected_return=accumulation_return_decimal,
            accumulation_volatility=accumulation_volatility_decimal,
            annual_contribution=annual_contribution_decimal,
            retirement_years=int(retirement_years),
            retirement_expected_return=retirement_return_decimal,
            retirement_volatility=retirement_volatility_decimal,
            annual_withdrawal=annual_withdrawal_decimal,
            simulations=int(simulations),
            random_seed=int(seed) if use_seed else None,
        )
        result = RunPortfolioRetirementPlan(
            get_portfolio_repository(), get_market_data_provider()
        ).execute(portfolio.name, assumptions)
    except (ApplicationError, DomainError) as exc:
        st.error(str(exc))
        return
    except Exception as exc:  # noqa: BLE001 - surface pydantic validation errors too
        st.error(f"Invalid inputs: {exc}")
        return

    plan = result.plan
    depletion_probability = float(plan.probability_of_depletion)

    st.subheader("Results")
    col1, col2, col3 = st.columns(3)
    col1.metric("Value at retirement (median)", str(plan.value_at_retirement_percentile_50))
    col2.metric("Value at end of retirement (median)", str(plan.value_at_end_percentile_50))
    col3.metric("Probability of running out of money", f"{depletion_probability:.1%}")

    if depletion_probability >= 0.5:
        st.error(
            "Over half of simulated paths ran out of money before the end of "
            "retirement. Consider a lower withdrawal rate, working longer, or "
            "adjusting the return/volatility assumptions."
        )
    elif depletion_probability >= 0.15:
        st.warning(
            "A meaningful share of simulated paths ran out of money. This plan "
            "carries real risk of depletion."
        )
    else:
        st.success("Most simulated paths did not run out of money under these assumptions.")

    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Outcome": "At retirement — 10th percentile",
                    "Value": str(plan.value_at_retirement_percentile_10),
                },
                {
                    "Outcome": "At retirement — median",
                    "Value": str(plan.value_at_retirement_percentile_50),
                },
                {
                    "Outcome": "At retirement — 90th percentile",
                    "Value": str(plan.value_at_retirement_percentile_90),
                },
                {"Outcome": "At end — 10th percentile", "Value": str(plan.value_at_end_percentile_10)},
                {"Outcome": "At end — median", "Value": str(plan.value_at_end_percentile_50)},
                {"Outcome": "At end — 90th percentile", "Value": str(plan.value_at_end_percentile_90)},
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )


render()
