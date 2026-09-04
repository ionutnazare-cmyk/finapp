from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from finapp.application.exceptions import BvbFetchError
from finapp.application.ports import DividendCacheWriter, DividendProvider
from finapp.application.use_cases.refresh_dividends_from_bvb import (
    RefreshDividendsFromBvb,
)
from finapp.domain.services.data_freshness import DataFreshnessPolicy
from finapp.domain.value_objects.dividend import Dividend
from finapp.domain.value_objects.enums import Currency
from finapp.domain.value_objects.money import Money


def _dividend(symbol: str, amount: str) -> Dividend:
    return Dividend(
        symbol=symbol,
        amount_per_share=Money(amount=Decimal(amount), currency=Currency.RON),
        pay_date=date(2026, 12, 31),
    )


class _FakeProvider(DividendProvider):
    """A fake provider — this test suite never makes a real HTTP call."""

    def __init__(
        self, dividends: dict[str, Dividend], fail_symbols: frozenset[str] = frozenset()
    ) -> None:
        self._dividends = dividends
        self._fail_symbols = fail_symbols

    def get_dividends(self, symbol: str) -> Sequence[Dividend]:
        if symbol in self._fail_symbols:
            raise BvbFetchError(symbol, "simulated failure")
        dividend = self._dividends.get(symbol)
        return (dividend,) if dividend is not None else ()


class _FakeCacheWriter(DividendCacheWriter):
    def __init__(self) -> None:
        self.saved: list[Dividend] = []

    def save_dividends(self, dividends: Iterable[Dividend]) -> None:
        self.saved.extend(dividends)


def test_skips_when_not_due() -> None:
    fetcher = _FakeProvider({"TLV": _dividend("TLV", "0.25")})
    writer = _FakeCacheWriter()
    policy = DataFreshnessPolicy(refresh_interval=timedelta(hours=1))
    use_case = RefreshDividendsFromBvb(fetcher, writer, policy)

    now = datetime(2026, 8, 28, 12, 0, tzinfo=UTC)
    result = use_case.execute(["TLV"], last_updated=now - timedelta(minutes=1), now=now)

    assert result.attempted is False
    assert writer.saved == []


def test_fetches_and_saves_when_due() -> None:
    fetcher = _FakeProvider({"TLV": _dividend("TLV", "0.25"), "SNP": _dividend("SNP", "0.04")})
    writer = _FakeCacheWriter()
    policy = DataFreshnessPolicy(refresh_interval=timedelta(hours=1))
    use_case = RefreshDividendsFromBvb(fetcher, writer, policy)

    now = datetime(2026, 8, 28, 12, 0, tzinfo=UTC)
    result = use_case.execute(["TLV", "SNP"], last_updated=None, now=now)

    assert result.attempted is True
    assert set(result.updated_symbols) == {"TLV", "SNP"}
    assert result.no_dividend_symbols == ()
    assert result.failed_symbols == ()
    assert len(writer.saved) == 2


def test_no_known_dividend_is_not_a_failure() -> None:
    fetcher = _FakeProvider({})
    writer = _FakeCacheWriter()
    policy = DataFreshnessPolicy(refresh_interval=timedelta(hours=1))
    use_case = RefreshDividendsFromBvb(fetcher, writer, policy)

    now = datetime(2026, 8, 28, 12, 0, tzinfo=UTC)
    result = use_case.execute(["H2O"], last_updated=None, now=now)

    assert result.no_dividend_symbols == ("H2O",)
    assert result.failed_symbols == ()
    assert writer.saved == []


def test_partial_failure_does_not_abort_batch() -> None:
    fetcher = _FakeProvider({"TLV": _dividend("TLV", "0.25")}, fail_symbols=frozenset({"BAD"}))
    writer = _FakeCacheWriter()
    policy = DataFreshnessPolicy(refresh_interval=timedelta(hours=1))
    use_case = RefreshDividendsFromBvb(fetcher, writer, policy)

    now = datetime(2026, 8, 28, 12, 0, tzinfo=UTC)
    result = use_case.execute(["TLV", "BAD"], last_updated=None, now=now)

    assert result.updated_symbols == ("TLV",)
    assert result.failed_symbols == ("BAD",)
    assert len(writer.saved) == 1
