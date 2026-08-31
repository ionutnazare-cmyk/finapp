"""Market data adapters implementing :class:`finapp.application.ports.MarketDataProvider`.

Note: :class:`~finapp.infrastructure.market_data.bvb_website_fetcher.BvbWebsiteFetcher`
is deliberately *not* imported here — it requires the optional ``bvb-live``
dependency group (``requests``, ``beautifulsoup4``), so importing it
eagerly would force those onto every user of this package. Import it
directly if you've installed that extra:
``from finapp.infrastructure.market_data.bvb_website_fetcher import BvbWebsiteFetcher``.
"""

from __future__ import annotations

from finapp.infrastructure.market_data.csv_provider import CsvMarketDataProvider
from finapp.infrastructure.market_data.csv_quote_cache_writer import CsvQuoteCacheWriter
from finapp.infrastructure.market_data.static_provider import StaticMarketDataProvider

__all__ = ["CsvMarketDataProvider", "CsvQuoteCacheWriter", "StaticMarketDataProvider"]
