"""A best-effort BVB website scraper for current prices and (single-figure)
annual dividends.

READ THIS BEFORE RELYING ON THIS ADAPTER:

- There is no currently-working public JSON/REST API for BVB data. BVB's
  documented API (``irapi.bvb.ro``, e.g.
  ``api/Trading/{symbol}/Prices/{period}``) returned HTTP 404 on every
  endpoint checked on 2026-08-28. Real-time/historical data is otherwise
  sold via a paid data-vending agreement (ICE Consolidated Feed) — see
  https://www.bvb.ro/Services/DataVending/ForDataVendors.
- This adapter instead scrapes the public per-instrument details page
  (e.g. ``https://bvb.ro/FinancialInstruments/Details/FinancialInstrumentsDetails.aspx?s=H2O``),
  extracting the "Ultimul pret" (last price) row from its price table, and
  the "Dividend (YYYY)" row from its indicators table. Verified against
  that exact page and both row labels on 2026-08-28 — if BVB changes the
  page layout or its Romanian labels, these parsers will break. When a
  parser can't find its expected row, :meth:`_parse_last_price` raises
  :class:`~finapp.application.exceptions.BvbFetchError` (a missing price
  is always an error); :meth:`get_dividends` instead returns an empty
  sequence (a missing dividend is normal — see its docstring).
- UNVERIFIED RISK: the page shows a "Loading..." placeholder ahead of its
  figures, which suggests they may be populated by client-side JavaScript
  after the initial page load. This adapter issues a plain HTTP GET (no
  JavaScript execution) and has *not* been confirmed to receive populated
  data that way — only a browser-rendered fetch was used to verify the
  page's structure. Test against the live site before relying on this in
  any unattended/scheduled context; if it raises "couldn't find a row," a
  JavaScript-capable fetcher (e.g. Playwright) would be needed instead of
  plain HTTP.
- Prices and dividends are assumed to be quoted in RON, correct for BVB's
  main market but not verified for foreign-currency-denominated
  instruments.
- DIVIDEND LIMITATIONS, specifically: BVB's "Dividend (YYYY)" indicator is
  a single trailing-year figure, not a full payment history — this
  adapter can only ever return the one dividend for whichever year BVB is
  currently showing, not prior years. Its exact pay/ex-dividend date also
  isn't given by that row (only the year is) — a real ex-dividend date
  *does* appear elsewhere on the page in a "Calendar Financiar" section,
  but parsing it reliably means matching Romanian month names in prose
  text, which was judged too fragile to build right now. This adapter
  therefore dates the dividend to December 31 of its indicated year as a
  documented placeholder, sufficient for sorting/recency comparisons but
  not a real pay date — don't rely on it for anything date-precise.
- Review https://bvb.ro/Disclaimer.aspx before using this beyond personal,
  non-commercial use — this adapter does not negotiate BVB's official
  data-vending terms.

Requires the optional ``bvb-live`` dependency group (``requests``,
``beautifulsoup4``); not installed by the base package.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation

import requests
from bs4 import BeautifulSoup

from finapp.application.dto import Quote
from finapp.application.exceptions import BvbFetchError
from finapp.application.ports import BvbDataFetcher, DividendProvider
from finapp.domain.value_objects.dividend import Dividend
from finapp.domain.value_objects.enums import Currency
from finapp.domain.value_objects.money import Money

_DETAILS_URL = "https://bvb.ro/FinancialInstruments/Details/FinancialInstrumentsDetails.aspx"
_LAST_PRICE_LABEL = "ultimul pret"
_DIVIDEND_LABEL_PATTERN = re.compile(r"dividend\s*\((\d{4})\)", re.IGNORECASE)


class BvbWebsiteFetcher(BvbDataFetcher, DividendProvider):
    """Scrapes bvb.ro's per-instrument details page for the current price
    and (a single trailing-year) dividend figure. See the module docstring
    above for important reliability and dividend-specific caveats.
    """

    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self._timeout_seconds = timeout_seconds

    def fetch_quote(self, symbol: str) -> Quote:
        normalized_symbol = symbol.strip().upper()
        html = self._fetch_page(normalized_symbol)
        price = self._parse_last_price(html, normalized_symbol)
        return Quote(
            symbol=normalized_symbol,
            price=Money(amount=price, currency=Currency.RON),
            as_of=datetime.now(UTC).date(),
        )

    def get_dividends(self, symbol: str) -> Sequence[Dividend]:
        """Return BVB's single trailing-year dividend figure for ``symbol``
        as a one-item sequence, or an empty sequence if the page has no
        "Dividend (YYYY)" row for it — a normal outcome for most
        instruments, not an error. Only a genuine fetch failure
        (network/HTTP error) raises
        :class:`~finapp.application.exceptions.BvbFetchError`.
        """

        normalized_symbol = symbol.strip().upper()
        html = self._fetch_page(normalized_symbol)
        dividend = self._parse_latest_dividend(html, normalized_symbol)
        return (dividend,) if dividend is not None else ()

    def _fetch_page(self, symbol: str) -> str:
        try:
            response = requests.get(
                _DETAILS_URL, params={"s": symbol}, timeout=self._timeout_seconds
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise BvbFetchError(symbol, str(exc)) from exc
        return response.text

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
    def _parse_latest_dividend(html: str, symbol: str) -> Dividend | None:
        soup = BeautifulSoup(html, "html.parser")
        for row in soup.find_all("tr"):
            cells = row.find_all(["td", "th"])
            if len(cells) < 2:
                continue
            match = _DIVIDEND_LABEL_PATTERN.search(cells[0].get_text(strip=True))
            if match is None:
                continue
            year = int(match.group(1))
            amount = BvbWebsiteFetcher._parse_ro_decimal(cells[1].get_text(strip=True), symbol)
            return Dividend(
                symbol=symbol,
                amount_per_share=Money(amount=amount, currency=Currency.RON),
                pay_date=date(year, 12, 31),
            )
        return None

    @staticmethod
    def _parse_ro_decimal(text: str, symbol: str) -> Decimal:
        # Romanian number format uses "." as a thousands separator and ","
        # as the decimal point, e.g. "83.213.474.895,00" -> 83213474895.00.
        normalized = text.replace(".", "").replace(",", ".")
        try:
            return Decimal(normalized)
        except InvalidOperation as exc:
            raise BvbFetchError(symbol, f"couldn't parse price value '{text}'") from exc
