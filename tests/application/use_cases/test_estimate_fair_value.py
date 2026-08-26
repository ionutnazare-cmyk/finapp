from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from finapp.application.dto import Quote
from finapp.application.exceptions import InvalidFairValueRequestError
from finapp.application.use_cases.estimate_fair_value import (
    EstimateFairValue,
    FairValueModel,
)
from finapp.domain.value_objects.enums import Currency
from finapp.domain.value_objects.money import Money
from finapp.infrastructure.market_data.static_provider import StaticMarketDataProvider


def _quote(symbol: str, amount: str) -> Quote:
    return Quote(
        symbol=symbol,
        price=Money(amount=Decimal(amount), currency=Currency.RON),
        as_of=date(2026, 8, 21),
    )


def test_gordon_growth_ddm_auto_fills_current_price_from_market_data() -> None:
    market_data = StaticMarketDataProvider({"TLV": _quote("TLV", "40.00")})
    use_case = EstimateFairValue(market_data_provider=market_data)

    estimate = use_case.execute(
        "TLV",
        FairValueModel.GORDON_GROWTH_DDM,
        dividend_per_share=Money(amount=Decimal("3.00"), currency=Currency.RON),
        required_return=Decimal("0.10"),
        dividend_growth_rate=Decimal("0.04"),
    )

    assert estimate.fair_value_per_share == Money(amount=Decimal("50.00"), currency=Currency.RON)
    assert estimate.current_price == Money(amount=Decimal("40.00"), currency=Currency.RON)
    assert estimate.margin_of_safety == Decimal("0.25")


def test_missing_quote_leaves_current_price_none() -> None:
    use_case = EstimateFairValue(market_data_provider=StaticMarketDataProvider({}))
    estimate = use_case.execute(
        "TLV",
        FairValueModel.DIVIDEND_YIELD_TARGET,
        dividend_per_share=Money(amount=Decimal("2.50"), currency=Currency.RON),
        target_yield=Decimal("0.05"),
    )
    assert estimate.current_price is None
    assert estimate.margin_of_safety is None


def test_no_market_data_provider_leaves_current_price_none() -> None:
    use_case = EstimateFairValue()
    estimate = use_case.execute(
        "H2O",
        FairValueModel.PRICE_TO_EARNINGS_RELATIVE,
        earnings_per_share=Money(amount=Decimal("4.00"), currency=Currency.RON),
        target_price_to_earnings=Decimal("15"),
    )
    assert estimate.fair_value_per_share == Money(amount=Decimal("60.00"), currency=Currency.RON)
    assert estimate.current_price is None


def test_missing_required_inputs_for_model_raises() -> None:
    use_case = EstimateFairValue()
    with pytest.raises(InvalidFairValueRequestError):
        use_case.execute("TLV", FairValueModel.GORDON_GROWTH_DDM)
