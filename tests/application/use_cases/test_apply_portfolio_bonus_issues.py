from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from finapp.application.exceptions import PortfolioNotFoundError
from finapp.application.use_cases.apply_portfolio_bonus_issues import (
    ApplyPortfolioBonusIssues,
)
from finapp.domain.entities.instrument import Instrument
from finapp.domain.entities.portfolio import Portfolio
from finapp.domain.value_objects.bonus_issue import BonusIssue
from finapp.domain.value_objects.enums import AssetType, Currency
from finapp.domain.value_objects.money import Money
from finapp.infrastructure.bonus_issues.static_provider import StaticBonusIssueProvider
from finapp.infrastructure.repositories.in_memory_portfolio_repository import (
    InMemoryPortfolioRepository,
)


def _bonus(symbol: str, ratio: str) -> BonusIssue:
    return BonusIssue(
        symbol=symbol, new_shares_per_held_share=Decimal(ratio), record_date=date(2026, 5, 1)
    )


@pytest.fixture
def repository() -> InMemoryPortfolioRepository:
    tlv = Instrument(
        symbol="TLV",
        name="Banca Transilvania",
        currency=Currency.RON,
        asset_type=AssetType.EQUITY,
    )
    snp = Instrument(
        symbol="SNP", name="OMV Petrom", currency=Currency.RON, asset_type=AssetType.EQUITY
    )
    portfolio = Portfolio(name="Retirement", base_currency=Currency.RON)
    portfolio.buy(tlv, Decimal("100"), Money(amount=Decimal("4"), currency=Currency.RON))
    portfolio.buy(snp, Decimal("1000"), Money(amount=Decimal("0.50"), currency=Currency.RON))
    repository = InMemoryPortfolioRepository()
    repository.save(portfolio)
    return repository


def test_applies_bonus_only_to_positions_with_known_issues(
    repository: InMemoryPortfolioRepository,
) -> None:
    provider = StaticBonusIssueProvider({"TLV": [_bonus("TLV", "0.25")]})
    use_case = ApplyPortfolioBonusIssues(repository, provider)

    result = use_case.execute("Retirement")

    assert len(result.applications) == 1
    application = result.applications[0]
    assert application.instrument.symbol == "TLV"
    assert application.quantity_before == Decimal("100")
    assert application.quantity_after == Decimal("125")
    assert application.additional_shares == Decimal("25")

    stored = repository.get("Retirement")
    assert stored is not None
    tlv_position = stored.get_position("TLV")
    assert tlv_position is not None
    assert tlv_position.quantity == Decimal("125")
    snp_position = stored.get_position("SNP")
    assert snp_position is not None
    assert snp_position.quantity == Decimal("1000")  # unaffected


def test_no_known_bonus_issues_gives_empty_result(
    repository: InMemoryPortfolioRepository,
) -> None:
    use_case = ApplyPortfolioBonusIssues(repository, StaticBonusIssueProvider({}))
    result = use_case.execute("Retirement")
    assert result.applications == ()


def test_missing_portfolio_raises() -> None:
    use_case = ApplyPortfolioBonusIssues(
        InMemoryPortfolioRepository(), StaticBonusIssueProvider({})
    )
    with pytest.raises(PortfolioNotFoundError):
        use_case.execute("Nonexistent")
