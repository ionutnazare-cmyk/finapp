"""Fair value estimation models for individual instruments.

A domain service, like ``monte_carlo`` and ``portfolio_optimizer``: pure
valuation math, no I/O. These are simplified, widely-taught equity
valuation models — a reasonable first cut at "is this cheap or expensive,"
not a substitute for full fundamental analysis. Each model returns a
per-share fair value in the same currency as its inputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from finapp.domain.exceptions import CurrencyMismatchError, FairValueModelError
from finapp.domain.value_objects.money import Money


@dataclass(frozen=True)
class FairValueEstimate:
    """The result of one fair value model applied to one instrument.

    ``current_price`` is optional — supply it to also get
    :attr:`margin_of_safety`, the fraction by which fair value exceeds
    current price (positive means undervalued, negative means overvalued).
    """

    symbol: str
    model: str
    fair_value_per_share: Money
    current_price: Money | None = None

    def __post_init__(self) -> None:
        if (
            self.current_price is not None
            and self.current_price.currency != self.fair_value_per_share.currency
        ):
            raise CurrencyMismatchError(
                expected=self.fair_value_per_share.currency.value,
                actual=self.current_price.currency.value,
            )

    @property
    def margin_of_safety(self) -> Decimal | None:
        if self.current_price is None or self.current_price.is_zero():
            return None
        diff = self.fair_value_per_share.amount - self.current_price.amount
        return diff / self.current_price.amount


class FairValueEstimator:
    """Simple, well-known per-share fair value models."""

    def gordon_growth_dividend_discount(
        self,
        symbol: str,
        next_annual_dividend_per_share: Money,
        required_return: Decimal,
        dividend_growth_rate: Decimal,
        current_price: Money | None = None,
    ) -> FairValueEstimate:
        """Gordon Growth (constant-growth) Dividend Discount Model:
        ``fair_value = D1 / (r - g)``.

        Requires ``required_return > dividend_growth_rate`` — a perpetuity
        growing at or faster than the rate used to discount it has no
        finite present value, so the model is undefined there.
        """

        if required_return <= dividend_growth_rate:
            raise FairValueModelError(
                f"required_return ({required_return}) must exceed "
                f"dividend_growth_rate ({dividend_growth_rate}) for the Gordon "
                f"Growth model to be defined"
            )
        spread = required_return - dividend_growth_rate
        fair_value = Money(
            amount=next_annual_dividend_per_share.amount / spread,
            currency=next_annual_dividend_per_share.currency,
        )
        return FairValueEstimate(
            symbol=symbol,
            model="gordon_growth_ddm",
            fair_value_per_share=fair_value,
            current_price=current_price,
        )

    def dividend_yield_target(
        self,
        symbol: str,
        annual_dividend_per_share: Money,
        target_yield: Decimal,
        current_price: Money | None = None,
    ) -> FairValueEstimate:
        """Fair value implied by a target dividend yield:
        ``fair_value = annual_dividend / target_yield``.

        Equivalent to the Gordon Growth model with zero assumed growth,
        expressed the way many dividend investors actually think ("what
        price gets me a 5% yield on this dividend?").
        """

        if target_yield <= Decimal("0"):
            raise FairValueModelError(f"target_yield must be positive, got {target_yield}")
        fair_value = Money(
            amount=annual_dividend_per_share.amount / target_yield,
            currency=annual_dividend_per_share.currency,
        )
        return FairValueEstimate(
            symbol=symbol,
            model="dividend_yield_target",
            fair_value_per_share=fair_value,
            current_price=current_price,
        )

    def price_to_earnings_relative(
        self,
        symbol: str,
        earnings_per_share: Money,
        target_price_to_earnings: Decimal,
        current_price: Money | None = None,
    ) -> FairValueEstimate:
        """Fair value from a target P/E multiple:
        ``fair_value = EPS * target P/E``.

        Requires positive earnings — P/E valuation is undefined for a
        loss-making instrument (a negative or zero P/E has no sensible
        interpretation here).
        """

        if target_price_to_earnings <= Decimal("0"):
            raise FairValueModelError(
                f"target_price_to_earnings must be positive, got {target_price_to_earnings}"
            )
        if earnings_per_share.amount <= Decimal("0"):
            raise FairValueModelError(
                "price_to_earnings_relative requires positive earnings_per_share "
                f"(got {earnings_per_share.amount})"
            )
        fair_value = Money(
            amount=earnings_per_share.amount * target_price_to_earnings,
            currency=earnings_per_share.currency,
        )
        return FairValueEstimate(
            symbol=symbol,
            model="price_to_earnings_relative",
            fair_value_per_share=fair_value,
            current_price=current_price,
        )
