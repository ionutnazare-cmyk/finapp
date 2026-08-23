"""Use case: apply every known bonus share issue across a portfolio's positions."""

from __future__ import annotations

from finapp.application.dto import BonusIssueApplication, PortfolioBonusIssueResult
from finapp.application.exceptions import PortfolioNotFoundError
from finapp.application.ports import BonusIssueProvider, PortfolioRepository


class ApplyPortfolioBonusIssues:
    """For each position, check for a known bonus share issue and apply it if
    found — adding shares at zero cost per
    :meth:`~finapp.domain.entities.portfolio.Portfolio.apply_bonus_issue`.

    Positions with no known bonus issue are skipped, not treated as an
    error: most instruments never issue bonus shares. TLV (Banca
    Transilvania) is BVB's most prominent example of a recurring issuer.
    """

    def __init__(
        self,
        portfolio_repository: PortfolioRepository,
        bonus_issue_provider: BonusIssueProvider,
    ) -> None:
        self._portfolio_repository = portfolio_repository
        self._bonus_issue_provider = bonus_issue_provider

    def execute(self, portfolio_name: str) -> PortfolioBonusIssueResult:
        portfolio = self._portfolio_repository.get(portfolio_name)
        if portfolio is None:
            raise PortfolioNotFoundError(portfolio_name)

        applications: list[BonusIssueApplication] = []
        for symbol, position in list(portfolio.positions.items()):
            bonus = self._bonus_issue_provider.get_latest_bonus_issue(symbol)
            if bonus is None:
                continue

            quantity_before = position.quantity
            updated = portfolio.apply_bonus_issue(bonus)
            applications.append(
                BonusIssueApplication(
                    instrument=updated.instrument,
                    bonus=bonus,
                    quantity_before=quantity_before,
                    quantity_after=updated.quantity,
                    additional_shares=updated.quantity - quantity_before,
                )
            )

        self._portfolio_repository.save(portfolio)

        return PortfolioBonusIssueResult(
            portfolio_name=portfolio.name,
            applications=tuple(applications),
        )
