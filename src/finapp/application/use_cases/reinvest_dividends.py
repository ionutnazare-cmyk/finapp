"""Use case: reinvest available dividend income back into more shares (DRIP)."""

from __future__ import annotations

from finapp.application.dto import DividendReinvestment, DividendReinvestmentResult
from finapp.application.exceptions import PortfolioNotFoundError, QuoteNotFoundError
from finapp.application.ports import DividendProvider, MarketDataProvider, PortfolioRepository
from finapp.domain.value_objects.money import Money


class ReinvestDividends:
    """For each position with a known dividend, buy more shares of the same
    instrument using that dividend's cash value at the current market price
    — a dividend reinvestment plan (DRIP).

    Positions with no known dividend, or whose dividend income rounds to
    zero, are skipped. A missing market quote for a position that *does*
    have dividend income to reinvest raises
    :class:`~finapp.application.exceptions.QuoteNotFoundError`, since a
    price is required to know how many shares to buy.
    """

    def __init__(
        self,
        portfolio_repository: PortfolioRepository,
        dividend_provider: DividendProvider,
        market_data_provider: MarketDataProvider,
    ) -> None:
        self._portfolio_repository = portfolio_repository
        self._dividend_provider = dividend_provider
        self._market_data_provider = market_data_provider

    def execute(self, portfolio_name: str) -> DividendReinvestmentResult:
        portfolio = self._portfolio_repository.get(portfolio_name)
        if portfolio is None:
            raise PortfolioNotFoundError(portfolio_name)

        dividend_cash: dict[str, Money] = {}
        for symbol, position in portfolio.positions.items():
            dividend = self._dividend_provider.get_latest_dividend(symbol)
            if dividend is None:
                continue
            income = position.dividend_income(dividend)
            if income.is_zero():
                continue
            dividend_cash[symbol] = income

        quotes = self._market_data_provider.get_quotes(dividend_cash.keys())

        reinvestments: list[DividendReinvestment] = []
        total_reinvested = Money.zero(portfolio.base_currency)
        for symbol, income in dividend_cash.items():
            quote = quotes.get(symbol)
            if quote is None:
                raise QuoteNotFoundError(symbol)

            instrument = portfolio.positions[symbol].instrument
            quantity = income.amount / quote.price.amount
            portfolio.buy(instrument, quantity, quote.price)

            reinvestments.append(
                DividendReinvestment(
                    instrument=instrument,
                    dividend_income=income,
                    price=quote.price,
                    quantity_purchased=quantity,
                )
            )
            total_reinvested = total_reinvested + income

        self._portfolio_repository.save(portfolio)

        return DividendReinvestmentResult(
            portfolio_name=portfolio.name,
            base_currency_total_reinvested=total_reinvested,
            reinvestments=tuple(reinvestments),
        )
