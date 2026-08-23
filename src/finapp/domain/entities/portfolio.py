"""The ``Portfolio`` aggregate root: a named collection of positions."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from decimal import Decimal
from types import MappingProxyType

from finapp.domain.entities.instrument import Instrument
from finapp.domain.entities.position import Position
from finapp.domain.exceptions import CurrencyMismatchError, UnknownInstrumentError
from finapp.domain.value_objects.bonus_issue import BonusIssue
from finapp.domain.value_objects.enums import Currency
from finapp.domain.value_objects.money import Money


class Portfolio:
    """A named collection of :class:`Position` objects, keyed by instrument symbol.

    ``Portfolio`` is the aggregate root for the domain model: all mutation of
    positions happens through its ``buy``/``sell`` methods, which enforce
    invariants (currency consistency, no over-selling) rather than allowing
    external code to manipulate positions directly. This is a mutable,
    encapsulated object — unlike the immutable ``Money``/``Instrument``/
    ``Position`` value objects and entities it composes.

    Currency conversion is out of scope for the domain layer. Aggregate
    totals (``total_market_value``, ``total_book_cost``) require every
    position to be priced in the portfolio's ``base_currency``; a mismatch
    raises :class:`CurrencyMismatchError`. Multi-currency support will be
    layered on top in a later sprint (e.g. via an FX-rate application
    service), not by relaxing this invariant.
    """

    def __init__(
        self,
        name: str,
        base_currency: Currency,
        positions: Iterable[Position] | None = None,
    ) -> None:
        if not name.strip():
            raise ValueError("Portfolio.name must not be blank")
        self._name = name
        self._base_currency = base_currency
        self._positions: dict[str, Position] = {}
        for position in positions or ():
            self._positions[position.instrument.symbol] = position

    @property
    def name(self) -> str:
        return self._name

    @property
    def base_currency(self) -> Currency:
        return self._base_currency

    @property
    def positions(self) -> Mapping[str, Position]:
        """Read-only view of current positions, keyed by symbol."""

        return MappingProxyType(self._positions)

    def get_position(self, symbol: str) -> Position | None:
        return self._positions.get(symbol.strip().upper())

    def buy(self, instrument: Instrument, quantity: Decimal, price: Money) -> Position:
        """Record a purchase of ``quantity`` shares of ``instrument`` at ``price``
        per share, creating a new position or merging into an existing one.

        Returns the resulting :class:`Position`.
        """

        existing = self._positions.get(instrument.symbol)
        if existing is None:
            new_position = Position(instrument=instrument, quantity=quantity, average_cost=price)
        else:
            new_position = existing.with_additional_shares(quantity, price)
        self._positions[instrument.symbol] = new_position
        return new_position

    def sell(self, symbol: str, quantity: Decimal) -> Position | None:
        """Record a sale of ``quantity`` shares of the position identified by
        ``symbol``. Returns the resulting :class:`Position`, or ``None`` if
        the position was fully closed (removed from the portfolio).

        Raises :class:`UnknownInstrumentError` if there is no position for
        ``symbol``, and :class:`InsufficientSharesError` (via ``Position``)
        if ``quantity`` exceeds the shares held.
        """

        normalized_symbol = symbol.strip().upper()
        existing = self._positions.get(normalized_symbol)
        if existing is None:
            raise UnknownInstrumentError(normalized_symbol)

        updated = existing.with_reduced_shares(quantity)
        if updated.is_closed():
            del self._positions[normalized_symbol]
            return None
        self._positions[normalized_symbol] = updated
        return updated

    def apply_bonus_issue(self, bonus: BonusIssue) -> Position:
        """Apply a bonus share issue to the position matching ``bonus.symbol``,
        adding shares at zero cost per :meth:`Position.with_bonus_shares`.

        Raises :class:`~finapp.domain.exceptions.UnknownInstrumentError` if
        this portfolio holds no position in that symbol.
        """

        existing = self._positions.get(bonus.symbol)
        if existing is None:
            raise UnknownInstrumentError(bonus.symbol)

        updated = existing.with_bonus_shares(bonus)
        self._positions[bonus.symbol] = updated
        return updated

    def total_book_cost(self) -> Money:
        """Sum of book cost across all positions, in ``base_currency``."""

        total = Money.zero(self._base_currency)
        for position in self._positions.values():
            total = total + self._to_base_currency(position.book_cost())
        return total

    def total_market_value(self, prices: Mapping[str, Money]) -> Money:
        """Sum of market value across all positions, in ``base_currency``.

        ``prices`` must contain a :class:`Money` entry for every symbol
        currently held; a missing entry raises :class:`UnknownInstrumentError`.
        """

        total = Money.zero(self._base_currency)
        for symbol, position in self._positions.items():
            price = prices.get(symbol)
            if price is None:
                raise UnknownInstrumentError(symbol)
            total = total + self._to_base_currency(position.market_value(price))
        return total

    def _to_base_currency(self, money: Money) -> Money:
        if money.currency != self._base_currency:
            raise CurrencyMismatchError(
                expected=self._base_currency.value, actual=money.currency.value
            )
        return money

    def is_empty(self) -> bool:
        return not self._positions

    def __len__(self) -> int:
        return len(self._positions)

    def __contains__(self, symbol: str) -> bool:
        return symbol.strip().upper() in self._positions

    def __repr__(self) -> str:
        return (
            f"Portfolio(name={self._name!r}, base_currency={self._base_currency.value}, "
            f"positions={len(self._positions)})"
        )
