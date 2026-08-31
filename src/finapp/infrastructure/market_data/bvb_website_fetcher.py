"""A best-effort BVB website scraper for current prices.

READ THIS BEFORE RELYING ON THIS ADAPTER:

- There is no currently-working public JSON/REST API for BVB data. BVB's
  documented API (``irapi.bvb.ro``, e.g.
  ``api/Trading/{symbol}/Prices/{period}``) returned HTTP 404 on every
  endpoint checked on 2026-08-28. Real-time/historical data is otherwise
  sold via a paid data-vending agreement (ICE Consolidated Feed) — see
  https://www.bvb.ro/Services/DataVending/ForDataVendors.
- This adapter instead scrapes the public per-instrument details page
  (e.g. ``https://bvb.ro/FinancialInstruments/Details/FinancialInstrumentsDetails.aspx?s=H2O``),
  extracting the "Ultimul pret" (last price) row from its price table.
  Verified against that exact page and row label on 2026-08-28 — if BVB
  changes the page layout or its Romanian labels, this parser will break.
  When it can't find the expected row, it raises
  :class:`~finapp.application.exceptions.BvbFetchError` explaining that,
  rather than silently returning a wrong or stale price.
- UNVERIFIED RISK: the page shows a "Loading..." placeholder ahead of its
  price figures, which suggests they may be populated by client-side
  JavaScript after the initial page load. This adapter issues a plain HTTP
  GET (no JavaScript execution) and has *not* been confirmed to receive a
  populated price table that way — only a browser-rendered fetch was used
  to verify the page's structure. Test ``fetch_quote`` against the live
  site before relying on it in any unattended/scheduled context; if it
  raises "couldn't find a row," a JavaScript-capable fetcher (e.g.
  Playwright) would be needed instead of plain HTTP.
- Prices are assumed to be quoted in RON, correct for BVB's main market but
  not verified for foreign-currency-denominated instruments.
- Dividend and bonus-issue data are *not* fetched here: BVB only publishes
  those as PDF announcements on this page, not as structured data.
- Review https://bvb.ro/Disclaimer.aspx before using this beyond personal,
  non-commercial use — this adapter does not negotiate BVB's official
  data-vending terms.

Requires the optional ``bvb-live`` dependency group (``requests``,
``beautifulsoup4``); not installed by the base package.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

import requests
from bs4 import BeautifulSoup

from finapp.application.dto import Quote
from finapp.application.exceptions import BvbFetchError
from finapp.application.ports import BvbDataFetcher
from finapp.domain.value_objects.enums import Currency
from finapp.domain.value_objects.money import Money

_DETAILS_URL = "https://bvb.ro/FinancialInstruments/Details/FinancialInstrumentsDetails.aspx"
_LAST_PRICE_LABEL = "ultimul pret"


class BvbWebsiteFetcher(BvbDataFetcher):
    """Scrapes bvb.ro's per-instrument details page for the current price.
    See the module docstring above for important reliability caveats.
    """

    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self._timeout_seconds = timeout_seconds

    def fetch_quote(self, symbol: str) -> Quote:
        normalized_symbol = symbol.strip().upper()
        try:
            response = requests.get(
                _DETAILS_URL, params={"s": normalized_symbol}, timeout=self._timeout_seconds
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise BvbFetchError(normalized_symbol, str(exc)) from exc

        price = self._parse_last_price(response.text, normalized_symbol)
        return Quote(
            symbol=normalized_symbol,
            price=Money(amount=price, currency=Currency.RON),
            as_of=datetime.now(UTC).date(),
        )

    @staticmethod
    def _parse_last_price(html: str, symbol: str) -> Decimal:
        soup = BeautifulSoup(html, "html.parser")
        for row in soup.find_all("tr"):
            cells = row.find_all(["td", "th"])
            if len(cells) < 2:
                continue
            label = cells[0].get_text(strip=True).lower()
            if label == _LAST_PRICE_LABEL:
                return BvbWebsiteFetcher._parse_ro_decimal(cells[1].get_text(strip=True), symbol)

        raise BvbFetchError(
            symbol,
            f"couldn't find a '{_LAST_PRICE_LABEL}' row in the page — BVB may have changed "
            "its page layout, or the price may be rendered by JavaScript this fetcher "
            "doesn't execute",
        )

    @staticmethod
    def _parse_ro_decimal(text: str, symbol: str) -> Decimal:
        # Romanian number format uses "." as a thousands separator and ","
        # as the decimal point, e.g. "83.213.474.895,00" -> 83213474895.00.
        normalized = text.replace(".", "").replace(",", ".")
        try:
            return Decimal(normalized)
        except InvalidOperation as exc:
            raise BvbFetchError(symbol, f"couldn't parse price value '{text}'") from exc
