"""Fair Value Estimator page.

Wraps the Sprint 1.12 fair value models. Per-instrument, not tied to a
stored portfolio — you can research a stock before ever buying it. If the
symbol has a quote in quotes.csv (in the chosen currency), the current
price is filled in automatically so you also get a margin-of-safety
reading.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

import streamlit as st

from finapp.application.exceptions import ApplicationError
from finapp.application.use_cases.estimate_fair_value import (
    EstimateFairValue,
    FairValueModel,
)
from finapp.domain.exceptions import DomainError
from finapp.domain.value_objects.enums import Currency
from finapp.domain.value_objects.money import Money
from finapp.presentation.streamlit_common import (
    format_money,
    format_percent,
    get_market_data_provider,
)

st.set_page_config(page_title="Fair Value — FinApp", page_icon="🔍", layout="wide")

_MODEL_LABELS = {
    FairValueModel.GORDON_GROWTH_DDM: "Gordon Growth Dividend Discount Model",
    FairValueModel.DIVIDEND_YIELD_TARGET: "Dividend Yield Target",
    FairValueModel.PRICE_TO_EARNINGS_RELATIVE: "Price-to-Earnings Relative",
}


def _to_decimal(raw: float, field_label: str) -> Decimal | None:
    try:
        return Decimal(str(raw))
    except InvalidOperation:
        st.error(f"'{field_label}' is not a valid number.")
        return None


def render() -> None:
    st.title("Fair Value Estimator 🔍")
    st.caption(
        "Simple, well-known valuation models — a first cut at 'is this cheap or "
        "expensive,' not a substitute for full fundamental analysis."
    )

    col_symbol, col_currency, col_model = st.columns(3)
    with col_symbol:
        symbol = st.text_input("Symbol", value="TLV").strip().upper()
    with col_currency:
        currency = st.selectbox("Currency", list(Currency))
    with col_model:
        model = st.selectbox(
            "Model", list(_MODEL_LABELS.keys()), format_func=lambda m: _MODEL_LABELS[m]
        )

    dividend_per_share_raw: float | None = None
    earnings_per_share_raw: float | None = None
    required_return_raw: float | None = None
    dividend_growth_rate_raw: float | None = None
    target_yield_raw: float | None = None
    target_pe_raw: float | None = None

    if model == FairValueModel.GORDON_GROWTH_DDM:
        col1, col2, col3 = st.columns(3)
        with col1:
            dividend_per_share_raw = st.number_input(
                "Next annual dividend/share", min_value=0.0, value=3.0, step=0.1, format="%.2f"
            )
        with col2:
            required_return_raw = st.number_input(
                "Required return (%)", value=10.0, step=0.5, format="%.2f"
            )
        with col3:
            dividend_growth_rate_raw = st.number_input(
                "Dividend growth rate (%)", value=4.0, step=0.5, format="%.2f"
            )
    elif model == FairValueModel.DIVIDEND_YIELD_TARGET:
        col1, col2 = st.columns(2)
        with col1:
            dividend_per_share_raw = st.number_input(
                "Annual dividend/share", min_value=0.0, value=2.5, step=0.1, format="%.2f"
            )
        with col2:
            target_yield_raw = st.number_input(
                "Target yield (%)", min_value=0.01, value=5.0, step=0.25, format="%.2f"
            )
    else:
        col1, col2 = st.columns(2)
        with col1:
            earnings_per_share_raw = st.number_input(
                "Earnings/share", value=4.0, step=0.1, format="%.2f"
            )
        with col2:
            target_pe_raw = st.number_input(
                "Target P/E multiple", min_value=0.01, value=15.0, step=0.5, format="%.2f"
            )

    if not symbol:
        st.info("Enter a symbol to get started.")
        return

    if not st.button("Estimate fair value"):
        return

    dividend_per_share = None
    if dividend_per_share_raw is not None:
        amount = _to_decimal(dividend_per_share_raw, "Dividend per share")
        if amount is None:
            return
        dividend_per_share = Money(amount=amount, currency=currency)

    earnings_per_share = None
    if earnings_per_share_raw is not None:
        amount = _to_decimal(earnings_per_share_raw, "Earnings per share")
        if amount is None:
            return
        earnings_per_share = Money(amount=amount, currency=currency)

    required_return = (
        _to_decimal(required_return_raw / 100, "Required return")
        if required_return_raw is not None
        else None
    )
    dividend_growth_rate = (
        _to_decimal(dividend_growth_rate_raw / 100, "Dividend growth rate")
        if dividend_growth_rate_raw is not None
        else None
    )
    target_yield = (
        _to_decimal(target_yield_raw / 100, "Target yield") if target_yield_raw is not None else None
    )
    target_price_to_earnings = (
        _to_decimal(target_pe_raw, "Target P/E") if target_pe_raw is not None else None
    )

    try:
        estimate = EstimateFairValue(market_data_provider=get_market_data_provider()).execute(
            symbol,
            model,
            dividend_per_share=dividend_per_share,
            earnings_per_share=earnings_per_share,
            required_return=required_return,
            dividend_growth_rate=dividend_growth_rate,
            target_yield=target_yield,
            target_price_to_earnings=target_price_to_earnings,
        )
    except (ApplicationError, DomainError) as exc:
        st.error(str(exc))
        return
    except Exception as exc:  # noqa: BLE001 - surface pydantic validation errors too
        st.error(f"Invalid inputs: {exc}")
        return

    st.subheader(f"{estimate.symbol} — {_MODEL_LABELS[model]}")
    col1, col2, col3 = st.columns(3)
    col1.metric("Fair value per share", format_money(estimate.fair_value_per_share))
    col2.metric(
        "Current price", format_money(estimate.current_price) if estimate.current_price else "—"
    )
    if estimate.margin_of_safety is not None:
        col3.metric("Margin of safety", format_percent(estimate.margin_of_safety))
        if estimate.margin_of_safety > 0:
            st.success("Trading below estimated fair value (potentially undervalued).")
        elif estimate.margin_of_safety < 0:
            st.warning("Trading above estimated fair value (potentially overvalued).")
    else:
        col3.metric("Margin of safety", "—")
        st.caption(
            f"No quote found for {estimate.symbol} in quotes.csv — add one to see "
            "margin of safety."
        )


render()
