from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from finapp.application.dto import Quote
from finapp.application.exceptions import BvbFetchError
from finapp.application.ports import BvbDataFetcher, QuoteCacheWriter
from finapp.application.use_cases.refresh_market_data_from_bvb import (
    RefreshMarketDataFromBvb,
)
from finapp.domain.services.data_freshness import DataFreshnessPolicy
from finapp.domain.value_objects.enums import Currency
from finapp.domain.value_objects.money import Money


class _FakeFetcher(BvbDataFetcher):
    """A fake fetcher — this test suite never makes a real HTTP call."""

    def __init__(self, prices: dict[str, str], fail_symbols: frozenset[str] = frozenset()) -> None:
        self._prices = prices
        self._fail_symbols = fail_symbols

    def fetch_quote(self, symbol: str) -> Quote:
        if symbol in self._fail_symbols:
            raise BvbFetchError(symbol, "simulated failure")
        return Quote(
            symbol=symbol,
            price=Money(amount=Decimal(self._prices[symbol]), currency=Currency.RON),
            as_of=date(2026, 8, 28),
        )


class _FakeCacheWriter(QuoteCacheWriter):
    def __init__(self) -> None:
        self.saved: list[Quote] = []

    def save_quotes(self, quotes: Iterable[Quote]) -> None:
        self.saved.extend(quotes)


def test_skips_when_not_due() -> None:
    fetcher = _FakeFetcher({"TLV": "5.00"})
    writer = _FakeCacheWriter()
    policy = DataFreshnessPolicy(refresh_interval=timedelta(hours=1))
    use_case = RefreshMarketDataFromBvb(fetcher, writer, policy)

    now = datetime(2026, 8, 28, 12, 0, tzinfo=UTC)
    result = use_case.execute(["TLV"], last_updated=now - timedelta(minutes=1), now=now)

    assert result.attempted is False
    assert writer.saved == []


def test_fetches_and_saves_when_due() -> None:
    fetcher = _FakeFetcher({"TLV": "5.00", "SNP": "0.55"})
    writer = _FakeCacheWriter()
    policy = DataFreshnessPolicy(refresh_interval=timedelta(hours=1))
    use_case = RefreshMarketDataFromBvb(fetcher, writer, policy)

    now = datetime(2026, 8, 28, 12, 0, tzinfo=UTC)
    result = use_case.execute(["TLV", "SNP"], last_updated=None, now=now)

    assert result.attempted is True
    assert set(result.updated_symbols) == {"TLV", "SNP"}
    assert result.failed_symbols == ()
    assert len(writer.saved) == 2


def test_partial_failure_does_not_abort_batch() -> None:
    fetcher = _FakeFetcher({"TLV": "5.00"}, fail_symbols=frozenset({"BAD"}))
    writer = _FakeCacheWriter()
    policy = DataFreshnessPolicy(refresh_interval=timedelta(hours=1))
    use_case = RefreshMarketDataFromBvb(fetcher, writer, policy)

    now = datetime(2026, 8, 28, 12, 0, tzinfo=UTC)
    result = use_case.execute(["TLV", "BAD"], last_updated=None, now=now)

    assert result.updated_symbols == ("TLV",)
    assert result.failed_symbols == ("BAD",)
    assert len(writer.saved) == 1


def test_no_writes_when_everything_fails() -> None:
    fetcher = _FakeFetcher({}, fail_symbols=frozenset({"BAD"}))
    writer = _FakeCacheWriter()
    policy = DataFreshnessPolicy(refresh_interval=timedelta(hours=1))
    use_case = RefreshMarketDataFromBvb(fetcher, writer, policy)

    now = datetime(2026, 8, 28, 12, 0, tzinfo=UTC)
    result = use_case.execute(["BAD"], last_updated=None, now=now)

    assert result.updated_symbols == ()
    assert result.failed_symbols == ("BAD",)
    assert writer.saved == []
