"""Use case: refresh local quote data from BVB, if a refresh is due."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from finapp.application.dto import MarketDataRefreshResult, Quote
from finapp.application.exceptions import BvbFetchError
from finapp.application.ports import BvbDataFetcher, QuoteCacheWriter
from finapp.domain.services.data_freshness import DataFreshnessPolicy


class RefreshMarketDataFromBvb:
    """Fetches current prices from BVB for the given symbols and writes them
    into the local quote cache — but only if the freshness policy says a
    refresh is actually due, so this can safely be called on every app
    startup or page load without hammering BVB's site every single time.

    A failure fetching one symbol doesn't abort the whole batch: it's
    recorded in ``failed_symbols`` and the rest proceed, since one broken
    or delisted ticker shouldn't block refreshing everything else.
    """

    def __init__(
        self,
        fetcher: BvbDataFetcher,
        cache_writer: QuoteCacheWriter,
        policy: DataFreshnessPolicy,
    ) -> None:
        self._fetcher = fetcher
        self._cache_writer = cache_writer
        self._policy = policy

    def execute(
        self,
        symbols: Sequence[str],
        last_updated: datetime | None,
        now: datetime,
    ) -> MarketDataRefreshResult:
        if not self._policy.is_due(last_updated, now):
            return MarketDataRefreshResult(
                attempted=False, updated_symbols=(), failed_symbols=(), as_of=now
            )

        updated: list[str] = []
        failed: list[str] = []
        quotes: list[Quote] = []
        for symbol in symbols:
            try:
                quotes.append(self._fetcher.fetch_quote(symbol))
                updated.append(symbol)
            except BvbFetchError:
                failed.append(symbol)

        if quotes:
            self._cache_writer.save_quotes(quotes)

        return MarketDataRefreshResult(
            attempted=True,
            updated_symbols=tuple(updated),
            failed_symbols=tuple(failed),
            as_of=now,
        )
