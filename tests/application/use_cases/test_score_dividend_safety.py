from __future__ import annotations

from datetime import date
from decimal import Decimal

from finapp.application.use_cases.score_dividend_safety import ScoreDividendSafety
from finapp.domain.services.dividend_safety import DividendSafetyRating
from finapp.domain.value_objects.dividend import Dividend
from finapp.domain.value_objects.enums import Currency
from finapp.domain.value_objects.money import Money
from finapp.infrastructure.dividends.static_provider import StaticDividendProvider


def _dividend(amount: str, year: int) -> Dividend:
    return Dividend(
        symbol="TLV",
        amount_per_share=Money(amount=Decimal(amount), currency=Currency.RON),
        pay_date=date(year, 6, 1),
    )


def test_auto_fills_history_from_dividend_provider() -> None:
    provider = StaticDividendProvider(
        {"TLV": [_dividend("1.00", 2024), _dividend("1.10", 2025), _dividend("1.20", 2026)]}
    )
    use_case = ScoreDividendSafety(dividend_provider=provider)

    result = use_case.execute("TLV", payout_ratio=Decimal("0.4"), debt_to_equity=Decimal("0.3"))

    assert result.overall_score == Decimal("100")
    assert result.rating == DividendSafetyRating.VERY_SAFE


def test_explicit_history_overrides_provider() -> None:
    provider = StaticDividendProvider({"TLV": [_dividend("1.00", 2024), _dividend("1.10", 2025)]})
    use_case = ScoreDividendSafety(dividend_provider=provider)

    explicit_history = (_dividend("2.00", 2025), _dividend("1.00", 2026))
    result = use_case.execute(
        "TLV",
        payout_ratio=Decimal("0.4"),
        debt_to_equity=Decimal("0.3"),
        dividend_history=explicit_history,
    )

    track_record = next(c for c in result.components if c.name == "dividend_track_record")
    assert track_record.score == Decimal("0")  # explicit history shows a recent cut


def test_no_provider_and_no_history_gives_neutral_track_record() -> None:
    use_case = ScoreDividendSafety()
    result = use_case.execute("TLV", payout_ratio=Decimal("0.4"), debt_to_equity=Decimal("0.3"))
    track_record = next(c for c in result.components if c.name == "dividend_track_record")
    assert track_record.score == Decimal("50")
