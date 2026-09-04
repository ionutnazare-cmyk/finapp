"""Dividend adapters implementing :class:`finapp.application.ports.DividendProvider`.

Note: a live BVB dividend fetcher also exists at
:class:`~finapp.infrastructure.market_data.bvb_website_fetcher.BvbWebsiteFetcher`
(it lives alongside the price fetcher since both scrape the same page).
It's deliberately not re-exported from here since it requires the
optional ``bvb-live`` dependency group.
"""

from __future__ import annotations

from finapp.infrastructure.dividends.csv_dividend_cache_writer import (
    CsvDividendCacheWriter,
)
from finapp.infrastructure.dividends.csv_provider import CsvDividendProvider
from finapp.infrastructure.dividends.static_provider import StaticDividendProvider

__all__ = ["CsvDividendCacheWriter", "CsvDividendProvider", "StaticDividendProvider"]
