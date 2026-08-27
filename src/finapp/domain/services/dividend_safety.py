"""Dividend safety scoring.

A domain service, like the other services in this package: pure scoring
logic with no I/O. Real dividend-safety analysis draws on a company's full
financial statements (payout ratio, free cash flow coverage, leverage,
earnings stability, dividend history) — this models a simplified,
transparent rule-based score from a handful of well-known inputs, not a
black-box or machine-learned score. Every component's score, weight, and
plain-language explanation is inspectable on the result.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from finapp.domain.exceptions import CurrencyMismatchError
from finapp.domain.value_objects.dividend import Dividend


class DividendSafetyRating(StrEnum):
    """A human-readable band for an overall dividend safety score (0-100)."""

    VERY_SAFE = "VERY_SAFE"
    SAFE = "SAFE"
    BORDERLINE = "BORDERLINE"
    UNSAFE = "UNSAFE"
    VERY_UNSAFE = "VERY_UNSAFE"


@dataclass(frozen=True)
class DividendSafetyInputs:
    """Inputs to the dividend safety score.

    ``payout_ratio`` is dividends paid divided by earnings (e.g.
    ``Decimal("0.6")`` for a 60% payout ratio) — pass ``None`` if the
    company has negative or zero earnings, rather than forcing a division
    that doesn't mean anything; a dividend paid from negative earnings is
    inherently concerning and scored accordingly. ``debt_to_equity`` is
    total debt divided by shareholder equity. ``dividend_history`` should
    be one representative annual dividend figure per year, oldest first,
    used to detect cuts, freezes, or consistent growth.
    """

    payout_ratio: Decimal | None
    debt_to_equity: Decimal
    dividend_history: tuple[Dividend, ...] = ()


@dataclass(frozen=True)
class DividendSafetyScoreComponent:
    """One factor's contribution to the overall score."""

    name: str
    score: Decimal
    weight: Decimal
    explanation: str


@dataclass(frozen=True)
class DividendSafetyScore:
    """The overall dividend safety score (0-100) and its rating band."""

    symbol: str
    overall_score: Decimal
    rating: DividendSafetyRating
    components: tuple[DividendSafetyScoreComponent, ...]


class DividendSafetyScorer:
    """Computes a transparent, rule-based dividend safety score (0-100) from
    payout ratio (40% weight), leverage (30%), and dividend track record
    (30%). The weights and breakpoints are simplifying assumptions, not a
    calibrated model — they're deliberately coarse (a handful of bands
    rather than a continuous curve) so every score is easy to explain.
    """

    _PAYOUT_WEIGHT = Decimal("0.4")
    _LEVERAGE_WEIGHT = Decimal("0.3")
    _TRACK_RECORD_WEIGHT = Decimal("0.3")

    def score(self, symbol: str, inputs: DividendSafetyInputs) -> DividendSafetyScore:
        payout_score, payout_explanation = self._score_payout_ratio(inputs.payout_ratio)
        leverage_score, leverage_explanation = self._score_leverage(inputs.debt_to_equity)
        track_record_score, track_record_explanation = self._score_track_record(
            inputs.dividend_history
        )

        components = (
            DividendSafetyScoreComponent(
                name="payout_ratio",
                score=payout_score,
                weight=self._PAYOUT_WEIGHT,
                explanation=payout_explanation,
            ),
            DividendSafetyScoreComponent(
                name="leverage",
                score=leverage_score,
                weight=self._LEVERAGE_WEIGHT,
                explanation=leverage_explanation,
            ),
            DividendSafetyScoreComponent(
                name="dividend_track_record",
                score=track_record_score,
                weight=self._TRACK_RECORD_WEIGHT,
                explanation=track_record_explanation,
            ),
        )
        overall = sum((c.score * c.weight for c in components), Decimal("0"))

        return DividendSafetyScore(
            symbol=symbol,
            overall_score=overall,
            rating=self._rating_for(overall),
            components=components,
        )

    @staticmethod
    def _score_payout_ratio(payout_ratio: Decimal | None) -> tuple[Decimal, str]:
        if payout_ratio is None:
            return (
                Decimal("0"),
                "Negative or zero earnings: the dividend isn't covered by earnings at all.",
            )
        if payout_ratio <= Decimal("0.5"):
            return Decimal("100"), f"Payout ratio {payout_ratio} is comfortably under 50%."
        if payout_ratio <= Decimal("0.75"):
            return Decimal("70"), f"Payout ratio {payout_ratio} is moderate (50-75%)."
        if payout_ratio <= Decimal("1.0"):
            return (
                Decimal("40"),
                f"Payout ratio {payout_ratio} is high (75-100%), leaving little room for error.",
            )
        return (
            Decimal("0"),
            f"Payout ratio {payout_ratio} exceeds 100%: paying out more than the company earns.",
        )

    @staticmethod
    def _score_leverage(debt_to_equity: Decimal) -> tuple[Decimal, str]:
        if debt_to_equity <= Decimal("0.5"):
            return Decimal("100"), f"Debt/equity of {debt_to_equity} is low."
        if debt_to_equity <= Decimal("1.0"):
            return Decimal("70"), f"Debt/equity of {debt_to_equity} is moderate."
        if debt_to_equity <= Decimal("2.0"):
            return Decimal("40"), f"Debt/equity of {debt_to_equity} is elevated."
        return Decimal("0"), f"Debt/equity of {debt_to_equity} is high, raising financial risk."

    @staticmethod
    def _score_track_record(history: tuple[Dividend, ...]) -> tuple[Decimal, str]:
        if len(history) < 2:
            return Decimal("50"), "Insufficient dividend history to assess a trend."

        currency = history[0].amount_per_share.currency
        for dividend in history:
            if dividend.amount_per_share.currency != currency:
                raise CurrencyMismatchError(
                    expected=currency.value, actual=dividend.amount_per_share.currency.value
                )

        changes = [
            history[i].amount_per_share.amount - history[i - 1].amount_per_share.amount
            for i in range(1, len(history))
        ]
        cuts = [change for change in changes if change < Decimal("0")]

        if changes[-1] < Decimal("0"):
            return Decimal("0"), "The most recent dividend change was a cut."
        if cuts:
            return Decimal("50"), "The dividend has been cut before, though not most recently."
        if all(change > Decimal("0") for change in changes):
            return Decimal("100"), "The dividend has increased every period on record."
        return (
            Decimal("75"),
            "The dividend has never been cut, but hasn't grown every period either.",
        )

    @staticmethod
    def _rating_for(score: Decimal) -> DividendSafetyRating:
        if score >= Decimal("80"):
            return DividendSafetyRating.VERY_SAFE
        if score >= Decimal("60"):
            return DividendSafetyRating.SAFE
        if score >= Decimal("40"):
            return DividendSafetyRating.BORDERLINE
        if score >= Decimal("20"):
            return DividendSafetyRating.UNSAFE
        return DividendSafetyRating.VERY_UNSAFE
