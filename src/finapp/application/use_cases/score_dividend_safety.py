"""Use case: score an instrument's dividend safety."""

from __future__ import annotations

from decimal import Decimal

from finapp.application.ports import DividendProvider
from finapp.domain.services.dividend_safety import (
    DividendSafetyInputs,
    DividendSafetyScore,
    DividendSafetyScorer,
)
from finapp.domain.value_objects.dividend import Dividend


class ScoreDividendSafety:
    """Score an instrument's dividend safety from its payout ratio, leverage,
    and dividend track record.

    If a ``dividend_provider`` is supplied and the caller doesn't pass
    ``dividend_history`` explicitly, the instrument's known dividend history
    is fetched automatically to assess its track record. This use case has
    no ``PortfolioRepository`` dependency, for the same reason as
    ``EstimateFairValue``: dividend safety is a property of the instrument
    itself, not of any specific portfolio holding it.
    """

    def __init__(
        self,
        scorer: DividendSafetyScorer | None = None,
        dividend_provider: DividendProvider | None = None,
    ) -> None:
        self._scorer = scorer or DividendSafetyScorer()
        self._dividend_provider = dividend_provider

    def execute(
        self,
        symbol: str,
        payout_ratio: Decimal | None,
        debt_to_equity: Decimal,
        dividend_history: tuple[Dividend, ...] | None = None,
    ) -> DividendSafetyScore:
        if dividend_history is not None:
            history = dividend_history
        elif self._dividend_provider is not None:
            history = tuple(self._dividend_provider.get_dividends(symbol))
        else:
            history = ()

        inputs = DividendSafetyInputs(
            payout_ratio=payout_ratio,
            debt_to_equity=debt_to_equity,
            dividend_history=history,
        )
        return self._scorer.score(symbol, inputs)
