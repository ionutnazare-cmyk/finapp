"""Use case: refresh local dividend data from BVB, if a refresh is due."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from finapp.application.dto import DividendRefreshResult
from finapp.application.exceptions import BvbFetchError
from finapp.application.ports import DividendCacheWriter, DividendProvider
from finapp.domain.services.data_freshness import DataFreshnessPolicy
from finapp.domain.value_objects.dividend import Dividend


class RefreshDividendsFromBvb:
    """Fetches known dividends from BVB for the given symbols and writes
    them into the local dividend cache — but only if the freshness policy
    says a refresh is actually due.

    Takes a plain :class:`~finapp.application.ports.DividendProvider` as
    its live source (rather than a bespoke fetcher port): BVB's page
    either has a dividend figure for a symbol or it doesn't, which is
    exactly the "empty means no known dividend, not an error" contract
    :class:`DividendProvider` already defines — no separate abstraction
    was needed here, unlike prices (see
    :class:`~finapp.application.ports.BvbDataFetcher`, where a missing
    quote *is* treated as an error).

    A symbol with no known dividend is recorded in ``no_dividend_symbols``,
    not ``failed_symbols`` — that's the normal case for most instruments,
    not a failure. A genuine fetch failure (network/HTTP error) for one
    symbol doesn't abort the batch.
    """

    def __init__(
        self,
        fetcher: DividendProvider,
        cache_writer: DividendCacheWriter,
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
    ) -> DividendRefreshResult:
        if not self._policy.is_due(last_updated, now):
            return DividendRefreshResult(
                attempted=False,
                updated_symbols=(),
                no_dividend_symbols=(),
                failed_symbols=(),
                as_of=now,
            )

        updated: list[str] = []
        no_dividend: list[str] = []
        failed: list[str] = []
        dividends: list[Dividend] = []
        for symbol in symbols:
            try:
                found = self._fetcher.get_dividends(symbol)
            except BvbFetchError:
                failed.append(symbol)
                continue

            if found:
                dividends.extend(found)
                updated.append(symbol)
            else:
                no_dividend.append(symbol)

        if dividends:
            self._cache_writer.save_dividends(dividends)

        return DividendRefreshResult(
            attempted=True,
            updated_symbols=tuple(updated),
            no_dividend_symbols=tuple(no_dividend),
            failed_symbols=tuple(failed),
            as_of=now,
        )
