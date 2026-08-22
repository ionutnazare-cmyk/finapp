"""Use case: compute a portfolio's current valuation using live market quotes."""

from __future__ import annotations

from finapp.application.dto import PortfolioValuation, PositionValuation
from finapp.application.exceptions import PortfolioNotFoundError, QuoteNotFoundError
from finapp.application.ports import MarketDataProvider, PortfolioRepository
from finapp.domain.entities.position import Position
from finapp.domain.value_objects.money import Money


class GetPortfolioValuation:
    """Compute a full valuation of the named portfolio using current market quotes.

    Combines the :class:`~finapp.domain.entities.portfolio.Portfolio`
    aggregate with a :class:`~finapp.application.ports.MarketDataProvider`
    to produce a :class:`~finapp.application.dto.PortfolioValuation`: totals
    plus a per-position breakdown.

    Raises :class:`~finapp.application.exceptions.PortfolioNotFoundError` if
    the portfolio doesn't exist, and
    :class:`~finapp.application.exceptions.QuoteNotFoundError` if the
    provider has no quote for a held symbol.
    """

    def __init__(
        self,
        portfolio_repository: PortfolioRepository,
        market_data_provider: MarketDataProvider,
    ) -> None:
        self._portfolio_repository = portfolio_repository
        self._market_data_provider = market_data_provider

    def execute(self, portfolio_name: str) -> PortfolioValuation:
        portfolio = self._portfolio_repository.get(portfolio_name)
        if portfolio is None:
            raise PortfolioNotFoundError(portfolio_name)

        quotes = self._market_data_provider.get_quotes(portfolio.positions.keys())

        position_valuations: list[PositionValuation] = []
        prices: dict[str, Money] = {}
        for symbol, position in portfolio.positions.items():
            quote = quotes.get(symbol)
            if quote is None:
                raise QuoteNotFoundError(symbol)
            prices[symbol] = quote.price
            position_valuations.append(self._value_position(position, quote.price))

        total_book_cost = portfolio.total_book_cost()
        total_market_value = portfolio.total_market_value(prices)
        total_unrealized_pnl = total_market_value - total_book_cost

        return PortfolioValuation(
            portfolio_name=portfolio.name,
            base_currency_total_book_cost=total_book_cost,
            base_currency_total_market_value=total_market_value,
            base_currency_total_unrealized_pnl=total_unrealized_pnl,
            positions=tuple(position_valuations),
        )

    @staticmethod
    def _value_position(position: Position, market_price: Money) -> PositionValuation:
        return PositionValuation(
            symbol=position.instrument.symbol,
            quantity=position.quantity,
            average_cost=position.average_cost,
            market_price=market_price,
            book_cost=position.book_cost(),
            market_value=position.market_value(market_price),
            unrealized_pnl=position.unrealized_pnl(market_price),
        )
