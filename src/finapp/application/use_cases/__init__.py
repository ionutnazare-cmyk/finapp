"""Application use cases: orchestration logic combining ports and domain entities.

Each use case is a small class with a single ``execute`` method and its
dependencies (ports) injected via the constructor, following the
Clean Architecture "interactor" pattern. This keeps use cases independently
testable with fake/in-memory ports, without needing real infrastructure.
"""

from __future__ import annotations

from finapp.application.use_cases.buy_shares import BuyShares
from finapp.application.use_cases.create_portfolio import CreatePortfolio
from finapp.application.use_cases.get_portfolio_valuation import GetPortfolioValuation
from finapp.application.use_cases.sell_shares import SellShares

__all__ = ["BuyShares", "CreatePortfolio", "GetPortfolioValuation", "SellShares"]
