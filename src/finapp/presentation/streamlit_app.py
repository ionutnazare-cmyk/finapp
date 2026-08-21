"""Streamlit dashboard entry point for FinApp.

Sprint 1.1 renders a placeholder landing page confirming the app boots and
that core dependencies (Streamlit, Plotly, Pandas) are wired correctly.
Real dashboard pages (portfolio overview, DCA planner, Monte Carlo results,
etc.) are introduced in later sprints.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from finapp import __version__
from finapp.config import get_settings


def render() -> None:
    """Render the Sprint 1.1 placeholder dashboard."""

    st.set_page_config(page_title="FinApp", page_icon="📈", layout="wide")

    settings = get_settings()

    st.title("FinApp 📈")
    st.caption(f"v{__version__} — project bootstrap (Sprint 1.1)")

    st.info(
        "This is a placeholder dashboard confirming the project scaffold "
        "runs end to end. Portfolio, DCA, dividend, and Monte Carlo views "
        "are introduced in later sprints."
    )

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Environment")
        st.write(
            {
                "environment": settings.environment.value,
                "base_currency": settings.base_currency,
                "data_dir": str(settings.data_dir),
            }
        )

    with col2:
        st.subheader("Dependency smoke test")
        sample = pd.DataFrame({"month": list(range(1, 13)), "value": [1] * 12})
        fig = go.Figure(
            data=[go.Bar(x=sample["month"], y=sample["value"], name="placeholder")]
        )
        fig.update_layout(
            title="Placeholder chart (Plotly + Pandas)",
            xaxis_title="Month",
            yaxis_title="Value",
            height=300,
        )
        st.plotly_chart(fig, use_container_width=True)


render()
