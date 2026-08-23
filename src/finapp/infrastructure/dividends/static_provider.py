"""An in-memory :class:`DividendProvider` backed by a fixed mapping of dividends."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from finapp.application.ports import DividendProvider
from finapp.domain.value_objects.dividend import Dividend


class StaticDividendProvider(DividendProvider):
    """A :class:`DividendProvider` backed by an in-memory mapping of dividend
    payments per symbol, sorted by pay date.

    Useful for unit tests, demos, and manual overrides before a live BVB
    dividend feed is wired in.
    """

    def __init__(self, dividends: Mapping[str, Sequence[Dividend]]) -> None:
        self._dividends: dict[str, list[Dividend]] = {
            symbol.strip().upper(): sorted(payments, key=lambda d: d.pay_date)
            for symbol, payments in dividends.items()
        }

    def get_dividends(self, symbol: str) -> Sequence[Dividend]:
        return tuple(self._dividends.get(symbol.strip().upper(), ()))
