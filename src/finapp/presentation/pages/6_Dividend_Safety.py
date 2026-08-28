"""Dividend Safety Score page.

Wraps the Sprint 1.13 rule-based scorer. Per-instrument, not tied to a
stored portfolio. If dividends.csv has history for the symbol, it's used
automatically to assess the dividend track record; you can also enter
history manually below to override it.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

import pandas as pd
import streamlit as st

from finapp.application.use_cases.score_dividend_safety import ScoreDividendSafety
from finapp.domain.exceptions import DomainError
from finapp.domain.services.dividend_safety import DividendSafetyRating
from finapp.domain.value_objects.dividend import Dividend
from finapp.domain.value_objects.enums import Currency
from finapp.domain.value_objects.money import Money
from finapp.presentation.streamlit_common import get_dividend_provider

st.set_page_config(page_title="Dividend Safety — FinApp", page_icon="🛡️", layout="wide")

_RATING_DISPLAY = {
    DividendSafetyRating.VERY_SAFE: ("Very safe", "success"),
    DividendSafetyRating.SAFE: ("Safe", "success"),
    DividendSafetyRating.BORDERLINE: ("Borderline", "warning"),
    DividendSafetyRating.UNSAFE: ("Unsafe", "error"),
    DividendSafetyRating.VERY_UNSAFE: ("Very unsafe", "error"),
}


def _to_decimal(raw: float, field_label: str) -> Decimal | None:
    try:
        return Decimal(str(raw))
    except InvalidOperation:
        st.error(f"'{field_label}' is not a valid number.")
        return None


def render() -> None:
    st.title("Dividend Safety Score 🛡️")
    st.caption(
        "A transparent, rule-based score (0-100) from payout ratio, leverage, and "
        "dividend track record — not a black box, and not a substitute for full "
        "fundamental analysis."
    )

    col1, col2 = st.columns(2)
    with col1:
        symbol = st.text_input("Symbol", value="TLV").strip().upper()
    with col2:
        currency = st.selectbox("Currency", list(Currency))

    col4, col5 = st.columns(2)
    with col4:
        has_earnings = st.checkbox("Company has positive earnings", value=True)
        payout_ratio_raw = st.number_input(
            "Payout ratio (%)", min_value=0.0, value=60.0, step=5.0, disabled=not has_earnings
        )
    with col5:
        debt_to_equity_raw = st.number_input(
            "Debt/equity", min_value=0.0, value=0.5, step=0.1, format="%.2f"
        )

    st.subheader("Dividend history")
    provider_history = get_dividend_provider().get_dividends(symbol) if symbol else ()
    if provider_history:
        st.caption(f"Found {len(provider_history)} known payment(s) for {symbol} in dividends.csv.")
        default_rows = pd.DataFrame(
            [
                {"Year": d.pay_date.year, "Amount per share": float(d.amount_per_share.amount)}
                for d in provider_history
            ]
        )
    else:
        st.caption(
            f"No known history for {symbol} in dividends.csv — enter it manually below, "
            "or leave empty to score with a neutral track record."
        )
        default_rows = pd.DataFrame([{"Year": date.today().year - 1, "Amount per share": 1.0}])

    history_rows = st.data_editor(default_rows, num_rows="dynamic", use_container_width=True)

    if not symbol:
        st.info("Enter a symbol to get started.")
        return

    if not st.button("Score dividend safety"):
        return

    payout_ratio = None
    if has_earnings:
        payout_ratio = _to_decimal(payout_ratio_raw / 100, "Payout ratio")
        if payout_ratio is None:
            return

    debt_to_equity = _to_decimal(debt_to_equity_raw, "Debt/equity")
    if debt_to_equity is None:
        return

    history: list[Dividend] = []
    for _, row in history_rows.iterrows():
        try:
            year = int(row["Year"])
        except (ValueError, TypeError):
            st.error(f"Invalid year: {row['Year']!r}")
            return
        amount = _to_decimal(float(row["Amount per share"]), "Amount per share")
        if amount is None:
            return
        history.append(
            Dividend(
                symbol=symbol,
                amount_per_share=Money(amount=amount, currency=currency),
                pay_date=date(year, 1, 1),
            )
        )
    history.sort(key=lambda d: d.pay_date)

    try:
        result = ScoreDividendSafety().execute(
            symbol,
            payout_ratio=payout_ratio,
            debt_to_equity=debt_to_equity,
            dividend_history=tuple(history),
        )
    except DomainError as exc:
        st.error(str(exc))
        return
    except Exception as exc:  # noqa: BLE001 - surface pydantic validation errors too
        st.error(f"Invalid inputs: {exc}")
        return

    label, style = _RATING_DISPLAY[result.rating]
    st.subheader(f"{result.symbol}: {float(result.overall_score):.1f} / 100 — {label}")
    getattr(st, style)(f"Overall rating: {label}")

    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Factor": c.name.replace("_", " ").title(),
                    "Score": f"{float(c.score):.0f}",
                    "Weight": f"{float(c.weight):.0%}",
                    "Explanation": c.explanation,
                }
                for c in result.components
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )


render()
