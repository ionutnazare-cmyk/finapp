from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from finapp.domain.exceptions import CurrencyMismatchError
from finapp.domain.services.dividend_safety import (
    DividendSafetyInputs,
    DividendSafetyRating,
    DividendSafetyScorer,
)
from finapp.domain.value_objects.dividend import Dividend
from finapp.domain.value_objects.enums import Currency
from finapp.domain.value_objects.money import Money


def _dividend(amount: str, year: int, currency: Currency = Currency.RON) -> Dividend:
    return Dividend(
        symbol="TLV",
        amount_per_share=Money(amount=Decimal(amount), currency=currency),
        pay_date=date(year, 6, 1),
    )


def test_best_case_scores_100_and_very_safe() -> None:
    history = (_dividend("1.00", 2024), _dividend("1.10", 2025), _dividend("1.20", 2026))
    inputs = DividendSafetyInputs(
        payout_ratio=Decimal("0.4"),
        debt_to_equity=Decimal("0.3"),
        dividend_history=history,
    )
    result = DividendSafetyScorer().score("TLV", inputs)

    assert result.overall_score == Decimal("100")
    assert result.rating == DividendSafetyRating.VERY_SAFE


def test_worst_case_scores_0_and_very_unsafe() -> None:
    history = (_dividend("2.00", 2025), _dividend("1.00", 2026))  # a cut, and it's the latest
    inputs = DividendSafetyInputs(
        payout_ratio=Decimal("1.2"),
        debt_to_equity=Decimal("2.5"),
        dividend_history=history,
    )
    result = DividendSafetyScorer().score("TLV", inputs)

    assert result.overall_score == Decimal("0")
    assert result.rating == DividendSafetyRating.VERY_UNSAFE


def test_moderate_case_matches_hand_computed_score() -> None:
    # payout 0.6 -> 70 (weight 0.4 -> 28.0)
    # debt/equity 0.8 -> 70 (weight 0.3 -> 21.0)
    # flat dividend history (no cuts, no consistent growth) -> 75 (weight 0.3 -> 22.5)
    # total = 71.5 -> SAFE
    history = (_dividend("2.00", 2024), _dividend("2.00", 2025), _dividend("2.00", 2026))
    inputs = DividendSafetyInputs(
        payout_ratio=Decimal("0.6"),
        debt_to_equity=Decimal("0.8"),
        dividend_history=history,
    )
    result = DividendSafetyScorer().score("TLV", inputs)

    assert result.overall_score == Decimal("71.5")
    assert result.rating == DividendSafetyRating.SAFE


def test_negative_earnings_payout_ratio_scores_zero_component() -> None:
    inputs = DividendSafetyInputs(
        payout_ratio=None,
        debt_to_equity=Decimal("0.3"),
        dividend_history=(),
    )
    result = DividendSafetyScorer().score("TLV", inputs)
    payout_component = next(c for c in result.components if c.name == "payout_ratio")
    assert payout_component.score == Decimal("0")


def test_past_cut_but_not_most_recent_scores_50_for_track_record() -> None:
    # 2.00 -> 1.50 (cut) -> 1.60 -> 1.70 (recovered, growing since)
    history = (
        _dividend("2.00", 2023),
        _dividend("1.50", 2024),
        _dividend("1.60", 2025),
        _dividend("1.70", 2026),
    )
    inputs = DividendSafetyInputs(
        payout_ratio=Decimal("0.4"), debt_to_equity=Decimal("0.3"), dividend_history=history
    )
    result = DividendSafetyScorer().score("TLV", inputs)
    track_record = next(c for c in result.components if c.name == "dividend_track_record")
    assert track_record.score == Decimal("50")


def test_insufficient_history_scores_50_for_track_record() -> None:
    inputs = DividendSafetyInputs(
        payout_ratio=Decimal("0.4"),
        debt_to_equity=Decimal("0.3"),
        dividend_history=(_dividend("1.00", 2026),),
    )
    result = DividendSafetyScorer().score("TLV", inputs)
    track_record = next(c for c in result.components if c.name == "dividend_track_record")
    assert track_record.score == Decimal("50")


def test_mismatched_currency_in_history_raises() -> None:
    history = (_dividend("1.00", 2025, Currency.RON), _dividend("1.10", 2026, Currency.USD))
    inputs = DividendSafetyInputs(
        payout_ratio=Decimal("0.4"), debt_to_equity=Decimal("0.3"), dividend_history=history
    )
    with pytest.raises(CurrencyMismatchError):
        DividendSafetyScorer().score("TLV", inputs)


def test_components_sum_to_overall_score() -> None:
    history = (_dividend("1.00", 2024), _dividend("1.10", 2025), _dividend("1.20", 2026))
    inputs = DividendSafetyInputs(
        payout_ratio=Decimal("0.6"), debt_to_equity=Decimal("1.5"), dividend_history=history
    )
    result = DividendSafetyScorer().score("TLV", inputs)
    total_weight = sum((c.weight for c in result.components), Decimal("0"))
    weighted_sum = sum((c.score * c.weight for c in result.components), Decimal("0"))
    assert total_weight == Decimal("1")
    assert weighted_sum == result.overall_score
