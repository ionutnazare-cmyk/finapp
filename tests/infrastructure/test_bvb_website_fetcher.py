"""Tests for the BVB scraper's HTML parsing logic only.

Deliberately does NOT test ``fetch_quote`` (the method that makes a real
HTTP request) — this test suite must stay hermetic and never depend on
bvb.ro being reachable or unchanged. See the module's docstring for how to
manually verify ``fetch_quote`` against the live site.
"""

from __future__ import annotations

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
