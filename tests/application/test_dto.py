from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from finapp.application.dto import Quote
from finapp.domain.value_objects.enums import Currency
from finapp.domain.value_objects.money import Money


def test_symbol_is_normalized_to_uppercase() -> None:
    quote = Quote(
        symbol="tlv",
        price=Money(amount=Decimal("4.5"), currency=Currency.RON),
        as_of=date(2026, 8, 21),
    )
    assert quote.symbol == "TLV"


def test_blank_symbol_rejected() -> None:
    with pytest.raises(Exception):  # noqa: B017 - pydantic ValidationError
        Quote(
            symbol="   ",
            price=Money(amount=Decimal("4.5"), currency=Currency.RON),
            as_of=date(2026, 8, 21),
        )


def test_quote_is_immutable() -> None:
    quote = Quote(
        symbol="TLV",
        price=Money(amount=Decimal("4.5"), currency=Currency.RON),
        as_of=date(2026, 8, 21),
    )
    with pytest.raises(Exception):  # noqa: B017 - pydantic ValidationError subclass
        quote.symbol = "SNP"  # type: ignore[misc]
