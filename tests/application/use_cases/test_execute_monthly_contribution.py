from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from finapp.application.dto import MonthlyContributionRequest, Quote
from finapp.application.exceptions import (
    InvalidAllocationError,
    PortfolioNotFoundError,
    QuoteNotFoundError,
)
from finapp.application.use_cases.execute_monthly_contribution import (
    ExecuteMonthlyContribution,
)
from finapp.domain.entities.instrument import Instrument
from finapp.domain.entities.portfolio import Portfolio
from finapp.domain.exceptions import CurrencyMismatchError
from finapp.domain.value_objects.enums import AssetType, Currency
from finapp.domain.value_objects.money import Money
from finapp.infrastructure.market_data.static_provider import StaticMarketDataProvider
from finapp.infrastructure.repositories.in_memory_portfolio_repository import (
    InMemoryPortfolioRepository,
)


def _quote(symbol: str, amount: str) -> Quote:
    return Quote(
        symbol=symbol,
        price=Money(amount=Decimal(amount), currency=Currency.RON),
        as_of=date(2026, 8, 21),
    )


@pytest.fixture
def tlv() -> Instrument:
    return Instrument(
        symbol="TLV",
        name="Banca Transilvania",
        currency=Currency.RON,
        asset_type=AssetType.EQUITY,
    )


@pytest.fixture
def snp() -> Instrument:
    return Instrument(
        symbol="SNP", name="OMV Petrom", currency=Currency.RON, asset_type=AssetType.EQUITY
    )


@pytest.fixture
def repository() -> InMemoryPortfolioRepository:
    repository = InMemoryPortfolioRepository()
    repository.save(Portfolio(name="Retirement", base_currency=Currency.RON))
    return repository


def test_splits_contribution_across_allocation(
    repository: InMemoryPortfolioRepository, tlv: Instrument, snp: Instrument
) -> None:
    market_data = StaticMarketDataProvider(
        {"TLV": _quote("TLV", "4.00"), "SNP": _quote("SNP", "0.50")}
    )
    use_case = ExecuteMonthlyContribution(repository, market_data)

    request = MonthlyContributionRequest(
        portfolio_name="Retirement",
        contribution=Money(amount=Decimal("1000"), currency=Currency.RON),
        allocation={tlv: Decimal("0.6"), snp: Decimal("0.4")},
    )
    result = use_case.execute(request)

    assert result.total_contribution == Money(amount=Decimal("1000"), currency=Currency.RON)
    by_symbol = {a.instrument.symbol: a for a in result.allocations}
    assert by_symbol["TLV"].allocated_cash == Money(amount=Decimal("600"), currency=Currency.RON)
    assert by_symbol["TLV"].quantity_purchased == Decimal("150")
    assert by_symbol["SNP"].allocated_cash == Money(amount=Decimal("400"), currency=Currency.RON)
    assert by_symbol["SNP"].quantity_purchased == Decimal("800")

    stored = repository.get("Retirement")
    assert stored is not None
    assert stored.get_position("TLV").quantity == Decimal("150")  # type: ignore[union-attr]
    assert stored.get_position("SNP").quantity == Decimal("800")  # type: ignore[union-attr]


def test_repeated_contribution_merges_into_existing_position(
    repository: InMemoryPortfolioRepository, tlv: Instrument
) -> None:
    use_case = ExecuteMonthlyContribution(
        repository, StaticMarketDataProvider({"TLV": _quote("TLV", "4.00")})
    )
    request = MonthlyContributionRequest(
        portfolio_name="Retirement",
        contribution=Money(amount=Decimal("400"), currency=Currency.RON),
        allocation={tlv: Decimal("1")},
    )
    use_case.execute(request)

    use_case_month_two = ExecuteMonthlyContribution(
        repository, StaticMarketDataProvider({"TLV": _quote("TLV", "5.00")})
    )
    use_case_month_two.execute(request)

    position = repository.get("Retirement").get_position("TLV")  # type: ignore[union-attr]
    assert position is not None
    assert position.quantity == Decimal("180")  # 100 @ 4.00 + 80 @ 5.00
    assert position.average_cost == Money(amount=Decimal("400") / Decimal("90"), currency=Currency.RON)


def test_empty_allocation_raises(repository: InMemoryPortfolioRepository) -> None:
    use_case = ExecuteMonthlyContribution(repository, StaticMarketDataProvider({}))
    request = MonthlyContributionRequest(
        portfolio_name="Retirement",
        contribution=Money(amount=Decimal("100"), currency=Currency.RON),
        allocation={},
    )
    with pytest.raises(InvalidAllocationError):
        use_case.execute(request)


def test_weights_not_summing_to_one_raises(
    repository: InMemoryPortfolioRepository, tlv: Instrument, snp: Instrument
) -> None:
    use_case = ExecuteMonthlyContribution(
        repository,
        StaticMarketDataProvider({"TLV": _quote("TLV", "4.00"), "SNP": _quote("SNP", "0.50")}),
    )
    request = MonthlyContributionRequest(
        portfolio_name="Retirement",
        contribution=Money(amount=Decimal("100"), currency=Currency.RON),
        allocation={tlv: Decimal("0.5"), snp: Decimal("0.6")},
    )
    with pytest.raises(InvalidAllocationError):
        use_case.execute(request)


def test_non_positive_weight_raises(
    repository: InMemoryPortfolioRepository, tlv: Instrument, snp: Instrument
) -> None:
    use_case = ExecuteMonthlyContribution(
        repository,
        StaticMarketDataProvider({"TLV": _quote("TLV", "4.00"), "SNP": _quote("SNP", "0.50")}),
    )
    request = MonthlyContributionRequest(
        portfolio_name="Retirement",
        contribution=Money(amount=Decimal("100"), currency=Currency.RON),
        allocation={tlv: Decimal("1.1"), snp: Decimal("-0.1")},
    )
    with pytest.raises(InvalidAllocationError):
        use_case.execute(request)


def test_missing_portfolio_raises(tlv: Instrument) -> None:
    use_case = ExecuteMonthlyContribution(
        InMemoryPortfolioRepository(), StaticMarketDataProvider({"TLV": _quote("TLV", "4.00")})
    )
    request = MonthlyContributionRequest(
        portfolio_name="Nonexistent",
        contribution=Money(amount=Decimal("100"), currency=Currency.RON),
        allocation={tlv: Decimal("1")},
    )
    with pytest.raises(PortfolioNotFoundError):
        use_case.execute(request)


def test_currency_mismatch_raises(
    repository: InMemoryPortfolioRepository, tlv: Instrument
) -> None:
    use_case = ExecuteMonthlyContribution(
        repository, StaticMarketDataProvider({"TLV": _quote("TLV", "4.00")})
    )
    request = MonthlyContributionRequest(
        portfolio_name="Retirement",
        contribution=Money(amount=Decimal("100"), currency=Currency.USD),
        allocation={tlv: Decimal("1")},
    )
    with pytest.raises(CurrencyMismatchError):
        use_case.execute(request)


def test_missing_quote_raises(repository: InMemoryPortfolioRepository, tlv: Instrument) -> None:
    use_case = ExecuteMonthlyContribution(repository, StaticMarketDataProvider({}))
    request = MonthlyContributionRequest(
        portfolio_name="Retirement",
        contribution=Money(amount=Decimal("100"), currency=Currency.RON),
        allocation={tlv: Decimal("1")},
    )
    with pytest.raises(QuoteNotFoundError):
        use_case.execute(request)
