"""Streamlit dashboard entry point (the "Home" page) for FinApp.

The actual portfolio features live in ``presentation/pages/`` — Streamlit
automatically turns files in that directory into a sidebar menu next to
this one. This page is just the welcome/landing screen and a summary of
where the app's editable data files live.
"""

from __future__ import annotations

import streamlit as st

from finapp import __version__
from finapp.presentation.streamlit_common import data_file_paths, get_portfolio_repository


def render() -> None:
    st.set_page_config(page_title="FinApp", page_icon="📈", layout="wide")

    st.title("FinApp 📈")
    st.caption(f"v{__version__} — dividend investing & retirement optimizer for the BVB")

    st.markdown(
        "Use **Portfolio Overview** in the sidebar to create a portfolio, "
        "buy/sell shares, and see valuation, dividend income, and bonus "
        "share issues."
    )

    repository = get_portfolio_repository()
    portfolio_names = repository.list_names()
    if portfolio_names:
        st.write(f"You have {len(portfolio_names)} portfolio(s): {', '.join(portfolio_names)}")
    else:
        st.info("No portfolios yet — head to **Portfolio Overview** to create your first one.")

    st.subheader("Data files")
    st.caption(
        "FinApp reads market prices, dividends, and bonus issues from local CSV "
        "files you maintain by hand for now — automatic BVB data updates are a "
        "later milestone. Edit these files directly to add or update data, then "
        "use the 'Reload data files' button on Portfolio Overview."
    )
    for label, path in data_file_paths().items():
        st.code(f"{label}: {path}", language=None)


render()
