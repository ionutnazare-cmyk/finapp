"""Tests for the BVB scraper's HTML parsing logic only.

Deliberately does NOT test ``fetch_quote`` (the method that makes a real
HTTP request) — this test suite must stay hermetic and never depend on
bvb.ro being reachable or unchanged. See the module's docstring for how to
manually verify ``fetch_quote`` against the live site.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from finapp.application.exceptions import BvbFetchError
from finapp.infrastructure.market_data.bvb_website_fetcher import BvbWebsiteFetcher

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "bvb_h2o_details_snippet.html"


def test_parses_last_price_from_verified_fixture() -> None:
    html = FIXTURE_PATH.read_text(encoding="utf-8")
    price = BvbWebsiteFetcher._parse_last_price(html, "H2O")
    assert price == Decimal("185.0000")


def test_parses_value_with_thousands_separator() -> None:
    html = "<table><tr><td>Ultimul pret</td><td>1.234,56</td></tr></table>"
    price = BvbWebsiteFetcher._parse_last_price(html, "TLV")
    assert price == Decimal("1234.56")


def test_label_matching_is_case_insensitive() -> None:
    html = "<table><tr><td>ULTIMUL PRET</td><td>10,50</td></tr></table>"
    price = BvbWebsiteFetcher._parse_last_price(html, "TLV")
    assert price == Decimal("10.50")


def test_missing_row_raises_bvb_fetch_error() -> None:
    html = "<table><tr><td>Something else</td><td>1,00</td></tr></table>"
    with pytest.raises(BvbFetchError):
        BvbWebsiteFetcher._parse_last_price(html, "TLV")


def test_unparseable_value_raises_bvb_fetch_error() -> None:
    html = "<table><tr><td>Ultimul pret</td><td>not-a-number</td></tr></table>"
    with pytest.raises(BvbFetchError):
        BvbWebsiteFetcher._parse_last_price(html, "TLV")


def test_empty_html_raises_bvb_fetch_error() -> None:
    with pytest.raises(BvbFetchError):
        BvbWebsiteFetcher._parse_last_price("<html></html>", "TLV")


def test_parses_latest_dividend_from_verified_fixture() -> None:
    html = FIXTURE_PATH.read_text(encoding="utf-8")
    dividend = BvbWebsiteFetcher._parse_latest_dividend(html, "H2O")
    assert dividend is not None
    assert dividend.amount_per_share.amount == Decimal("9.571562")
    assert dividend.pay_date == date(2025, 12, 31)


def test_dividend_label_year_is_extracted() -> None:
    html = "<table><tr><td>Dividend (2024)</td><td>1,50</td></tr></table>"
    dividend = BvbWebsiteFetcher._parse_latest_dividend(html, "TLV")
    assert dividend is not None
    assert dividend.pay_date.year == 2024
    assert dividend.amount_per_share.amount == Decimal("1.50")


def test_no_dividend_row_returns_none_not_an_error() -> None:
    html = "<table><tr><td>PER</td><td>18,54</td></tr></table>"
    dividend = BvbWebsiteFetcher._parse_latest_dividend(html, "TLV")
    assert dividend is None


def test_get_dividends_returns_empty_tuple_when_no_row(monkeypatch: pytest.MonkeyPatch) -> None:
    fetcher = BvbWebsiteFetcher()
    monkeypatch.setattr(fetcher, "_fetch_page", lambda symbol: "<table></table>")
    assert fetcher.get_dividends("TLV") == ()


def test_get_dividends_returns_one_item_when_found(monkeypatch: pytest.MonkeyPatch) -> None:
    fetcher = BvbWebsiteFetcher()
    html = "<table><tr><td>Dividend (2025)</td><td>0,25</td></tr></table>"
    monkeypatch.setattr(fetcher, "_fetch_page", lambda symbol: html)
    dividends = fetcher.get_dividends("TLV")
    assert len(dividends) == 1
    assert dividends[0].amount_per_share.amount == Decimal("0.25")
