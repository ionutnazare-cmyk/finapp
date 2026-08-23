"""Shared Streamlit helpers.

Every page under ``presentation/pages/`` imports from here so they all work
against the same underlying data — one JSON-file portfolio store and three
local CSV caches (quotes, dividends, bonus issues) living under the
configured ``data_dir`` (see :mod:`finapp.config`). This module is not
itself a page: Streamlit only auto-lists files directly inside ``pages/``
in its sidebar menu.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from finapp.config import get_settings
from finapp.infrastructure.bonus_issues.csv_provider import CsvBonusIssueProvider
from finapp.infrastructure.dividends.csv_provider import CsvDividendProvider
from finapp.infrastructure.market_data.csv_provider import CsvMarketDataProvider
from finapp.infrastructure.repositories.json_portfolio_repository import (
    JsonPortfolioRepository,
)

_QUOTES_HEADER = "symbol,price,currency,as_of\n"
_DIVIDENDS_HEADER = "symbol,amount_per_share,currency,pay_date\n"
_BONUS_ISSUES_HEADER = "symbol,new_shares_per_held_share,record_date\n"


def _ensure_csv_exists(path: Path, header: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(header, encoding="utf-8")


def data_file_paths() -> dict[str, Path]:
    """Where each editable data file lives, for display in the UI."""

    settings = get_settings()
    return {
        "Portfolios": settings.data_dir / "portfolios",
        "Quotes": settings.data_dir / "quotes.csv",
        "Dividends": settings.data_dir / "dividends.csv",
        "Bonus issues": settings.data_dir / "bonus_issues.csv",
    }


@st.cache_resource
def get_portfolio_repository() -> JsonPortfolioRepository:
    settings = get_settings()
    return JsonPortfolioRepository(settings.data_dir / "portfolios")


@st.cache_resource
def get_market_data_provider() -> CsvMarketDataProvider:
    settings = get_settings()
    path = settings.data_dir / "quotes.csv"
    _ensure_csv_exists(path, _QUOTES_HEADER)
    return CsvMarketDataProvider(path)


@st.cache_resource
def get_dividend_provider() -> CsvDividendProvider:
    settings = get_settings()
    path = settings.data_dir / "dividends.csv"
    _ensure_csv_exists(path, _DIVIDENDS_HEADER)
    return CsvDividendProvider(path)


@st.cache_resource
def get_bonus_issue_provider() -> CsvBonusIssueProvider:
    settings = get_settings()
    path = settings.data_dir / "bonus_issues.csv"
    _ensure_csv_exists(path, _BONUS_ISSUES_HEADER)
    return CsvBonusIssueProvider(path)


def refresh_all_providers() -> None:
    """Reload all three CSV-backed providers from disk.

    Call this (then ``st.rerun()``) after the user edits a data file
    externally while the app is running.
    """

    get_market_data_provider().refresh()
    get_dividend_provider().refresh()
    get_bonus_issue_provider().refresh()
