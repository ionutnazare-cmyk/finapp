"""Use case: estimate an instrument's fair value using a chosen model."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from finapp.application.exceptions import InvalidFairValueRequestError, QuoteNotFoundError
from finapp.application.ports import MarketDataProvider
from finapp.domain.services.fair_value import FairValueEstimate, FairValueEstimator
from finapp.domain.value_objects.money import Money


class FairValueModel(StrEnum):
    """Which fair value model to apply."""

    GORDON_GROWTH_DDM = "GORDON_GROWTH_DDM"
    DIVIDEND_YIELD_TARGET = "DIVIDEND_YIELD_TARGET"
    PRICE_TO_EARNINGS_RELATIVE = "PRICE_TO_EARNINGS_RELATIVE"


class EstimateFairValue:
    """Estimate an instrument's fair value using a chosen model.

    If a ``market_data_provider`` is supplied and has a quote for the
    symbol, the current price is attached automatically (populating
    ``FairValueEstimate.margin_of_safety``); otherwise the estimate is
    returned without one. This use case has no ``PortfolioRepository``
    dependency — fair value estimation is naturally per instrument, not
    tied to any specific portfolio, since you might be researching a stock
    you don't yet own.
    """

    def __init__(
        self,
        estimator: FairValueEstimator | None = None,
        market_data_provider: MarketDataProvider | None = None,
    ) -> None:
        self._estimator = estimator or FairValueEstimator()
        self._market_data_provider = market_data_provider

    def execute(
        self,
        symbol: str,
        model: FairValueModel,
        *,
        dividend_per_share: Money | None = None,
        earnings_per_share: Money | None = None,
        required_return: Decimal | None = None,
        dividend_growth_rate: Decimal | None = None,
        target_yield: Decimal | None = None,
        target_price_to_earnings: Decimal | None = None,
    ) -> FairValueEstimate:
        current_price = self._lookup_current_price(symbol)

        if model == FairValueModel.GORDON_GROWTH_DDM:
            if dividend_per_share is None or required_return is None or dividend_growth_rate is None:
                raise InvalidFairValueRequestError(
                    "GORDON_GROWTH_DDM requires dividend_per_share, required_return, "
                    "and dividend_growth_rate"
                )
            return self._estimator.gordon_growth_dividend_discount(
                symbol, dividend_per_share, required_return, dividend_growth_rate, current_price
            )

        if model == FairValueModel.DIVIDEND_YIELD_TARGET:
            if dividend_per_share is None or target_yield is None:
                raise InvalidFairValueRequestError(
                    "DIVIDEND_YIELD_TARGET requires dividend_per_share and target_yield"
                )
            return self._estimator.dividend_yield_target(
                symbol, dividend_per_share, target_yield, current_price
            )

        if earnings_per_share is None or target_price_to_earnings is None:
            raise InvalidFairValueRequestError(
                "PRICE_TO_EARNINGS_RELATIVE requires earnings_per_share and "
                "target_price_to_earnings"
            )
        return self._estimator.price_to_earnings_relative(
            symbol, earnings_per_share, target_price_to_earnings, current_price
        )

    def _lookup_current_price(self, symbol: str) -> Money | None:
        if self._market_data_provider is None:
            return None
        try:
            return self._market_data_provider.get_quote(symbol).price
        except QuoteNotFoundError:
            return None
