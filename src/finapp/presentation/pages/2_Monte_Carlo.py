"""Monte Carlo Simulation page.

Projects a portfolio's future value distribution (not whether it survives
withdrawals — see Retirement Planning for that) using the domain-level
Monte Carlo engine from Sprint 1.9, starting from the portfolio's current
market value.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

import pandas as pd
import streamlit as st

from finapp.application.exceptions import ApplicationError
from finapp.application.use_cases.run_portfolio_monte_carlo_simulation import (
    RunPortfolioMonteCarloSimulation,
)
from finapp.domain.exceptions import DomainError
from finapp.domain.services.monte_carlo import MonteCarloAssumptions
from finapp.presentation.streamlit_common import (
    get_market_data_provider,
    get_portfolio_repository,
    select_or_create_portfolio,
)

st.set_page_config(page_title="Monte Carlo — FinApp", page_icon="🎲", layout="wide")


def _to_decimal(raw: float, field_label: str) -> Decimal | None:
    try:
        return Decimal(str(raw))
    except InvalidOperation:
        st.error(f"'{field_label}' is not a valid number.")
        return None


def render() -> None:
    st.title("Monte Carlo Simulation 🎲")
    st.caption(
        "Projects a range of future portfolio values under random annual returns. "
        "This answers 'how big might my portfolio get' — for 'will my money last "
        "through retirement withdrawals,' see the Retirement Planning page."
    )

    portfolio = select_or_create_portfolio(key_prefix="mc")
    if portfolio is None:
        st.info("Select or create a portfolio in the sidebar to get started.")
        return

    if portfolio.is_empty():
        st.info("This portfolio has no positions yet — buy something first on Portfolio Overview.")
        return

    with st.form("monte_carlo_form"):
        col1, col2 = st.columns(2)
        with col1:
            expected_return = st.number_input(
                "Expected annual return (%)", value=7.0, step=0.5, format="%.2f"
            )
            volatility = st.number_input(
                "Annual volatility (%)", min_value=0.0, value=15.0, step=0.5, format="%.2f"
            )
            years = st.number_input("Years", min_value=1, max_value=100, value=20, step=1)
        with col2:
            annual_contribution = st.number_input(
                f"Annual contribution ({portfolio.base_currency.value})",
                min_value=0.0,
                value=0.0,
                step=100.0,
                format="%.2f",
            )
            simulations = st.number_input(
                "Simulations", min_value=100, max_value=200_000, value=5000, step=100
            )
            use_seed = st.checkbox("Use a fixed random seed (reproducible results)", value=True)
            seed = st.number_input("Seed", value=42, step=1, disabled=not use_seed)
        submitted = st.form_submit_button("Run simulation")

    if not submitted:
        return

    expected_return_decimal = _to_decimal(expected_return / 100, "Expected annual return")
    volatility_decimal = _to_decimal(volatility / 100, "Annual volatility")
    contribution_decimal = _to_decimal(annual_contribution, "Annual contribution")
    if expected_return_decimal is None or volatility_decimal is None or contribution_decimal is None:
        return

    try:
        assumptions = MonteCarloAssumptions(
            expected_annual_return=expected_return_decimal,
            annual_volatility=volatility_decimal,
            years=int(years),
            simulations=int(simulations),
            annual_contribution=contribution_decimal,
            random_seed=int(seed) if use_seed else None,
        )
        result = RunPortfolioMonteCarloSimulation(
            get_portfolio_repository(), get_market_data_provider()
        ).execute(portfolio.name, assumptions)
    except (ApplicationError, DomainError) as exc:
        st.error(str(exc))
        return
    except Exception as exc:  # noqa: BLE001 - surface pydantic validation errors too
        st.error(f"Invalid inputs: {exc}")
        return

    simulation = result.simulation
    st.subheader(f"Results after {int(years)} years ({int(simulations):,} simulations)")

    col1, col2, col3 = st.columns(3)
    col1.metric("Starting value", str(simulation.starting_value))
    col2.metric("Median ending value", str(simulation.percentile_50))
    col3.metric("Probability of ending below starting value", f"{float(simulation.probability_of_loss):.1%}")

    st.dataframe(
        pd.DataFrame(
            [
                {"Outcome": "10th percentile (pessimistic)", "Value": str(simulation.percentile_10)},
                {"Outcome": "50th percentile (median)", "Value": str(simulation.percentile_50)},
                {"Outcome": "90th percentile (optimistic)", "Value": str(simulation.percentile_90)},
                {"Outcome": "Mean", "Value": str(simulation.mean)},
                {"Outcome": "Minimum", "Value": str(simulation.minimum)},
                {"Outcome": "Maximum", "Value": str(simulation.maximum)},
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )
    st.caption(
        "Returns are modeled as independent annual draws (no year-to-year correlation, "
        "no fat tails) — a simplifying assumption, not a full market model."
    )


render()
