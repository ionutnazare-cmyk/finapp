"""Portfolio Overview page.

Lets the user create or select a portfolio, buy/sell shares, and see:
current valuation (book cost, market value, P&L), dividend income, known
bonus share issues, and a monthly DCA contribution tool — exercising every
use case built in Sprints 1.4 through 1.7 against locally maintained CSV
data (see the Home page for where those files live).
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

import pandas as pd
import plotly.express as px
import streamlit as st

from finapp.application.dto import MonthlyContributionRequest
from finapp.application.exceptions import ApplicationError
from finapp.application.use_cases.apply_portfolio_bonus_issues import (
    ApplyPortfolioBonusIssues,
)
from finapp.application.use_cases.buy_shares import BuyShares
from finapp.application.use_cases.edit_position import EditPosition
from finapp.application.use_cases.execute_monthly_contribution import (
    ExecuteMonthlyContribution,
)
from finapp.application.use_cases.get_portfolio_dividend_income import (
    GetPortfolioDividendIncome,
)
from finapp.application.use_cases.get_portfolio_valuation import GetPortfolioValuation
from finapp.application.use_cases.reinvest_dividends import ReinvestDividends
from finapp.application.use_cases.sell_shares import SellShares
from finapp.domain.entities.instrument import Instrument
from finapp.domain.entities.portfolio import Portfolio
from finapp.domain.exceptions import DomainError
from finapp.domain.value_objects.enums import AssetType
from finapp.domain.value_objects.money import Money
from finapp.presentation.streamlit_common import (
    format_money,
    format_number,
    get_bonus_issue_provider,
    get_dividend_provider,
    get_market_data_provider,
    get_portfolio_repository,
    maybe_refresh_bvb_dividends,
    maybe_refresh_bvb_prices,
    refresh_all_providers,
    select_or_create_portfolio,
)

st.set_page_config(page_title="Portfolio Overview — FinApp", page_icon="📊", layout="wide")


def _to_decimal(raw: float, field_label: str) -> Decimal | None:
    """Convert a Streamlit numeric widget's float value to Decimal safely.

    Going through ``str()`` first avoids binary floating-point artifacts
    (e.g. ``Decimal(0.1)`` != ``Decimal('0.1')``) — the domain layer only
    ever works with ``Decimal``, never ``float``.
    """

    try:
        return Decimal(str(raw))
    except InvalidOperation:
        st.error(f"'{field_label}' is not a valid number.")
        return None


def _render_overview_tab(portfolio: Portfolio) -> None:
    market_data_provider = get_market_data_provider()

    if portfolio.is_empty():
        st.info("This portfolio has no positions yet — use the Buy / Sell tab to add one.")
        return

    try:
        valuation = GetPortfolioValuation(get_portfolio_repository(), market_data_provider).execute(
            portfolio.name
        )
    except (ApplicationError, DomainError) as exc:
        st.warning(
            f"Couldn't compute full valuation: {exc}. Add the missing symbol(s) to "
            f"quotes.csv, then use 'Reload data files' below."
        )
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("Book cost", format_money(valuation.base_currency_total_book_cost))
    col2.metric("Market value", format_money(valuation.base_currency_total_market_value))
    col3.metric("Unrealized P&L", format_money(valuation.base_currency_total_unrealized_pnl))

    rows = [
        {
            "Symbol": p.symbol,
            "Quantity": float(p.quantity),
            "Avg. cost": float(p.average_cost.amount),
            "Price": float(p.market_price.amount),
            "Book cost": float(p.book_cost.amount),
            "Market value": float(p.market_value.amount),
            "Unrealized P&L": float(p.unrealized_pnl.amount),
        }
        for p in valuation.positions
    ]
    positions_df = pd.DataFrame(rows)

    st.caption(
        "Quantity and Avg. cost are editable — use this to fix a data-entry mistake "
        "or set a cost basis for shares you already owned. This does not apply "
        "weighted-average-cost math like Buy does; it replaces the figures outright. "
        "Other columns are computed and read-only."
    )
    edited_df = st.data_editor(
        positions_df,
        column_config={
            "Symbol": st.column_config.TextColumn(disabled=True),
            "Quantity": st.column_config.NumberColumn(format="%.2f"),
            "Avg. cost": st.column_config.NumberColumn(format="%.2f"),
            "Price": st.column_config.NumberColumn(format="%.2f", disabled=True),
            "Book cost": st.column_config.NumberColumn(format="%.2f", disabled=True),
            "Market value": st.column_config.NumberColumn(format="%.2f", disabled=True),
            "Unrealized P&L": st.column_config.NumberColumn(format="%.2f", disabled=True),
        },
        hide_index=True,
        use_container_width=True,
        num_rows="fixed",
        key="positions_editor",
    )

    if st.button("Apply changes to positions"):
        changed_rows = [
            edited_row
            for _, edited_row in edited_df.iterrows()
            if not positions_df[positions_df["Symbol"] == edited_row["Symbol"]].empty
            and (
                float(edited_row["Quantity"])
                != float(
                    positions_df.loc[
                        positions_df["Symbol"] == edited_row["Symbol"], "Quantity"
                    ].iloc[0]
                )
                or float(edited_row["Avg. cost"])
                != float(
                    positions_df.loc[
                        positions_df["Symbol"] == edited_row["Symbol"], "Avg. cost"
                    ].iloc[0]
                )
            )
        ]

        if not changed_rows:
            st.info("No changes to apply.")
        else:
            repository = get_portfolio_repository()
            applied = 0
            for edited_row in changed_rows:
                symbol = str(edited_row["Symbol"])
                quantity = _to_decimal(float(edited_row["Quantity"]), f"{symbol} quantity")
                avg_cost = _to_decimal(float(edited_row["Avg. cost"]), f"{symbol} avg. cost")
                if quantity is None or avg_cost is None:
                    continue
                if quantity < 0 or avg_cost < 0:
                    st.error(f"{symbol}: quantity and avg. cost must be non-negative.")
                    continue
                try:
                    EditPosition(repository).execute(
                        portfolio.name,
                        symbol,
                        quantity,
                        Money(amount=avg_cost, currency=portfolio.base_currency),
                    )
                    applied += 1
                except (ApplicationError, DomainError) as exc:
                    st.error(f"{symbol}: {exc}")
            if applied:
                st.success(f"Applied changes to {applied} position(s).")
                st.rerun()

    if len(rows) > 1:
        fig = px.pie(
            pd.DataFrame(rows), names="Symbol", values="Market value", title="Allocation by market value"
        )
        st.plotly_chart(fig, use_container_width=True)


def _render_buy_sell_tab(portfolio: Portfolio) -> None:
    repository = get_portfolio_repository()
    held_symbols = list(portfolio.positions.keys())

    st.subheader("Buy more of a holding")
    if not held_symbols:
        st.caption("No existing holdings yet — use 'Buy a new instrument' below.")
    else:
        with st.form("buy_existing_form"):
            symbol = st.selectbox("Symbol", held_symbols)
            quantity = st.number_input("Quantity", min_value=0.0, step=1.0, format="%.2f")
            price = st.number_input(
                f"Price per share ({portfolio.base_currency.value})",
                min_value=0.0,
                step=0.01,
                format="%.2f",
            )
            submitted = st.form_submit_button("Buy")
        if submitted:
            qty = _to_decimal(quantity, "Quantity")
            px_amount = _to_decimal(price, "Price per share")
            if qty is not None and px_amount is not None:
                if qty <= 0 or px_amount <= 0:
                    st.error("Quantity and price must both be greater than zero.")
                else:
                    instrument = portfolio.get_position(symbol).instrument  # type: ignore[union-attr]
                    try:
                        BuyShares(repository).execute(
                            portfolio.name,
                            instrument,
                            qty,
                            Money(amount=px_amount, currency=portfolio.base_currency),
                        )
                        st.success(f"Bought {qty} shares of {symbol}.")
                        st.rerun()
                    except (ApplicationError, DomainError) as exc:
                        st.error(str(exc))

    st.divider()
    st.subheader("Buy a new instrument")
    st.caption(f"Priced in the portfolio's base currency ({portfolio.base_currency.value}).")
    with st.form("buy_new_form"):
        new_symbol = st.text_input("Symbol (e.g. TLV)")
        new_name = st.text_input("Company name")
        asset_type = st.selectbox("Asset type", list(AssetType))
        exchange = st.text_input("Exchange", value="BVB")
        isin = st.text_input("ISIN (optional, 12 characters)")
        new_quantity = st.number_input(
            "Quantity", min_value=0.0, step=1.0, format="%.2f", key="new_qty"
        )
        new_price = st.number_input(
            "Price per share", min_value=0.0, step=0.01, format="%.2f", key="new_price"
        )
        submitted_new = st.form_submit_button("Buy new instrument")

    if submitted_new:
        qty = _to_decimal(new_quantity, "Quantity")
        px_amount = _to_decimal(new_price, "Price per share")
        if qty is not None and px_amount is not None:
            if not new_symbol.strip() or not new_name.strip():
                st.error("Symbol and company name are required.")
            elif qty <= 0 or px_amount <= 0:
                st.error("Quantity and price must both be greater than zero.")
            else:
                try:
                    instrument = Instrument(
                        symbol=new_symbol,
                        name=new_name,
                        currency=portfolio.base_currency,
                        asset_type=asset_type,
                        exchange=exchange or "BVB",
                        isin=isin.strip() or None,
                    )
                    BuyShares(repository).execute(
                        portfolio.name,
                        instrument,
                        qty,
                        Money(amount=px_amount, currency=portfolio.base_currency),
                    )
                    st.success(f"Bought {qty} shares of {instrument.symbol}.")
                    st.rerun()
                except (ApplicationError, DomainError) as exc:
                    st.error(str(exc))
                except Exception as exc:  # noqa: BLE001 - surface any validation error to the user
                    st.error(f"Couldn't create instrument: {exc}")

    st.divider()
    st.subheader("Sell shares")
    if not held_symbols:
        st.caption("No holdings to sell.")
        return
    with st.form("sell_form"):
        sell_symbol = st.selectbox("Symbol", held_symbols, key="sell_symbol")
        sell_quantity = st.number_input("Quantity", min_value=0.0, step=1.0, format="%.2f")
        submitted_sell = st.form_submit_button("Sell")
    if submitted_sell:
        qty = _to_decimal(sell_quantity, "Quantity")
        if qty is not None:
            if qty <= 0:
                st.error("Quantity must be greater than zero.")
            else:
                try:
                    SellShares(repository).execute(portfolio.name, sell_symbol, qty)
                    st.success(f"Sold {qty} shares of {sell_symbol}.")
                    st.rerun()
                except (ApplicationError, DomainError) as exc:
                    st.error(str(exc))


def _render_dividends_tab(portfolio: Portfolio) -> None:
    repository = get_portfolio_repository()
    dividend_provider = get_dividend_provider()

    if portfolio.is_empty():
        st.info("No positions yet.")
        return

    held_symbols = list(portfolio.positions.keys())

    with st.expander("Live BVB dividends (experimental)"):
        with st.spinner("Checking BVB for dividend updates..."):
            auto_result = maybe_refresh_bvb_dividends(held_symbols)

        if auto_result is None:
            st.caption(
                "Install `uv sync --extra bvb-live` to enable automatic dividend "
                "fetching from BVB — see README. Note this only ever gives one "
                "trailing-year figure per symbol, not a full payment history."
            )
        else:
            if auto_result.updated_symbols:
                st.success(f"Refreshed from BVB: {', '.join(auto_result.updated_symbols)}")
            if auto_result.no_dividend_symbols:
                st.caption(
                    f"No known dividend on BVB for: {', '.join(auto_result.no_dividend_symbols)}"
                )
            if auto_result.failed_symbols:
                st.warning(f"Couldn't fetch from BVB: {', '.join(auto_result.failed_symbols)}")
            if st.button("Force refresh dividends now"):
                with st.spinner("Fetching latest dividends from BVB..."):
                    forced_result = maybe_refresh_bvb_dividends(held_symbols, force=True)
                if forced_result is not None and forced_result.updated_symbols:
                    st.success(f"Refreshed from BVB: {', '.join(forced_result.updated_symbols)}")
                if forced_result is not None and forced_result.failed_symbols:
                    st.warning(
                        f"Couldn't fetch from BVB: {', '.join(forced_result.failed_symbols)}"
                    )
                st.rerun()

    income = GetPortfolioDividendIncome(repository, dividend_provider).execute(portfolio.name)
    if not income.incomes:
        st.info(
            "No known dividends for any held position. Add rows to dividends.csv, "
            "then use 'Reload data files' below."
        )
    else:
        rows = [
            {
                "Symbol": i.instrument.symbol,
                "Quantity held": format_number(i.quantity_held),
                "Amount/share": format_number(i.dividend.amount_per_share.amount),
                "Pay date": i.dividend.pay_date.isoformat(),
                "Total income": format_number(i.total_income.amount),
            }
            for i in income.incomes
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.metric("Total dividend income", format_money(income.base_currency_total_income))

        st.caption(
            "Reinvesting uses the most recently known dividend for each position. "
            "Running it again without new data in dividends.csv will reinvest the "
            "same dividend a second time — this sprint doesn't yet track which "
            "payments have already been processed."
        )
        if st.button("Reinvest dividends now"):
            try:
                result = ReinvestDividends(
                    repository, dividend_provider, get_market_data_provider()
                ).execute(portfolio.name)
                st.success(
                    f"Reinvested {result.base_currency_total_reinvested} across "
                    f"{len(result.reinvestments)} position(s)."
                )
                st.rerun()
            except (ApplicationError, DomainError) as exc:
                st.error(str(exc))


def _render_bonus_issues_tab(portfolio: Portfolio) -> None:
    if portfolio.is_empty():
        st.info("No positions yet.")
        return

    st.caption(
        "Checks each position for its most recently known bonus issue and applies "
        "it. Like dividend reinvestment, running this again without new data in "
        "bonus_issues.csv will re-apply the same event a second time."
    )
    if st.button("Check & apply known bonus issues"):
        try:
            result = ApplyPortfolioBonusIssues(
                get_portfolio_repository(), get_bonus_issue_provider()
            ).execute(portfolio.name)
        except (ApplicationError, DomainError) as exc:
            st.error(str(exc))
            return

        if not result.applications:
            st.info("No known bonus issues for any held position.")
        else:
            rows = [
                {
                    "Symbol": a.instrument.symbol,
                    "Ratio (new/held)": format_number(a.bonus.new_shares_per_held_share),
                    "Quantity before": format_number(a.quantity_before),
                    "Quantity after": format_number(a.quantity_after),
                    "New shares": format_number(a.additional_shares),
                }
                for a in result.applications
            ]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            st.success(f"Applied {len(result.applications)} bonus issue(s).")


def _render_dca_tab(portfolio: Portfolio) -> None:
    repository = get_portfolio_repository()
    held_symbols = list(portfolio.positions.keys())

    if not held_symbols:
        st.info("Buy at least one position first to use monthly DCA allocation.")
        return

    st.caption(
        "Splits a monthly contribution across your existing holdings by target "
        "weight (must sum to 100%) and buys accordingly at current market prices."
    )
    contribution = st.number_input(
        f"Monthly contribution ({portfolio.base_currency.value})",
        min_value=0.0,
        step=10.0,
        format="%.2f",
    )
    equal_share = round(100.0 / len(held_symbols), 2)
    weights: dict[str, float] = {}
    for symbol in held_symbols:
        weights[symbol] = st.number_input(
            f"{symbol} weight (%)",
            min_value=0.0,
            max_value=100.0,
            value=equal_share,
            step=1.0,
            key=f"dca_weight_{symbol}",
        )

    st.caption("Weights must sum to exactly 100% — adjust if the equal split doesn't divide evenly.")
    if st.button("Execute monthly contribution"):
        contribution_amount = _to_decimal(contribution, "Monthly contribution")
        if contribution_amount is None or contribution_amount <= 0:
            st.error("Contribution must be greater than zero.")
            return

        allocation: dict[Instrument, Decimal] = {}
        for symbol, weight_percent in weights.items():
            weight_decimal = _to_decimal(weight_percent, f"{symbol} weight")
            if weight_decimal is None:
                return
            if weight_decimal > 0:
                instrument = portfolio.get_position(symbol).instrument  # type: ignore[union-attr]
                allocation[instrument] = weight_decimal / Decimal("100")

        request = MonthlyContributionRequest(
            portfolio_name=portfolio.name,
            contribution=Money(amount=contribution_amount, currency=portfolio.base_currency),
            allocation=allocation,
        )
        try:
            result = ExecuteMonthlyContribution(repository, get_market_data_provider()).execute(
                request
            )
            st.success(f"Invested {result.total_contribution} across {len(result.allocations)} position(s).")
            st.rerun()
        except (ApplicationError, DomainError) as exc:
            st.error(str(exc))


def render() -> None:
    st.title("Portfolio Overview")

    portfolio = select_or_create_portfolio()

    if st.sidebar.button("Reload data files"):
        refresh_all_providers()
        st.sidebar.success("Reloaded quotes, dividends, and bonus issues from disk.")
        st.rerun()

    if portfolio is not None and not portfolio.is_empty():
        st.sidebar.divider()
        st.sidebar.subheader("Live BVB prices (experimental)")
        held_symbols = list(portfolio.positions.keys())

        with st.spinner("Checking BVB for price updates..."):
            auto_result = maybe_refresh_bvb_prices(held_symbols)

        if auto_result is None:
            st.sidebar.caption(
                "Install `uv sync --extra bvb-live` to enable automatic price "
                "fetching from BVB — see README for reliability caveats."
            )
        else:
            if auto_result.updated_symbols:
                st.sidebar.success(
                    f"Refreshed from BVB: {', '.join(auto_result.updated_symbols)}"
                )
            if auto_result.failed_symbols:
                st.sidebar.warning(
                    f"Couldn't fetch from BVB: {', '.join(auto_result.failed_symbols)}"
                )
            if st.sidebar.button("Force refresh now"):
                with st.spinner("Fetching latest prices from BVB..."):
                    forced_result = maybe_refresh_bvb_prices(held_symbols, force=True)
                if forced_result is not None and forced_result.updated_symbols:
                    st.sidebar.success(
                        f"Refreshed from BVB: {', '.join(forced_result.updated_symbols)}"
                    )
                if forced_result is not None and forced_result.failed_symbols:
                    st.sidebar.warning(
                        f"Couldn't fetch from BVB: {', '.join(forced_result.failed_symbols)}"
                    )
                st.rerun()

    if portfolio is None:
        st.info("Select or create a portfolio in the sidebar to get started.")
        return

    st.caption(f"Base currency: {portfolio.base_currency.value}")

    tabs = st.tabs(["Overview", "Buy / Sell", "Dividends", "Bonus issues", "Monthly DCA"])
    with tabs[0]:
        _render_overview_tab(portfolio)
    with tabs[1]:
        _render_buy_sell_tab(portfolio)
    with tabs[2]:
        _render_dividends_tab(portfolio)
    with tabs[3]:
        _render_bonus_issues_tab(portfolio)
    with tabs[4]:
        _render_dca_tab(portfolio)


render()
