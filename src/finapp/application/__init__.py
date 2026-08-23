"""Application layer: use cases and ports (interfaces).

Rules for this package (see ``docs/ARCHITECTURE.md``):

- Depends only on ``finapp.domain``.
- Defines abstract ports (e.g. ``MarketDataProvider``, ``PortfolioRepository``,
  ``ReportExporter``) that the infrastructure layer implements.
- Contains orchestration logic (use cases) but no concrete I/O.

Sprint 1.1 established this package as empty scaffolding. Sprint 1.3 added
the first port and its supporting DTO:

- ``finapp.application.ports``: ``MarketDataProvider`` (abstract interface).
- ``finapp.application.dto``: ``Quote`` (data returned by ports).
- ``finapp.application.exceptions``: application-level error types.

Sprint 1.4 added the ``PortfolioRepository`` port and the first use cases:

- ``finapp.application.ports.PortfolioRepository``: load/save portfolios.
- ``finapp.application.use_cases``: ``CreatePortfolio``, ``BuyShares``,
  ``SellShares``, ``GetPortfolioValuation``.
- ``finapp.application.dto``: ``PositionValuation``, ``PortfolioValuation``.

Sprint 1.5 added monthly DCA (dollar-cost averaging) investing:

- ``finapp.application.use_cases.ExecuteMonthlyContribution``: splits a
  fixed contribution across a target allocation and buys accordingly.
- ``finapp.application.dto``: ``MonthlyContributionRequest``,
  ``DcaAllocationResult``, ``MonthlyContributionResult``.
- ``finapp.application.exceptions.InvalidAllocationError``.

Sprint 1.6 added dividend tracking and reinvestment:

- ``finapp.application.ports.DividendProvider``: known dividend payments
  per instrument.
- ``finapp.application.use_cases``: ``GetPortfolioDividendIncome``,
  ``ReinvestDividends`` (a DRIP — dividend reinvestment plan).
- ``finapp.application.dto``: ``DividendIncome``, ``PortfolioDividendIncome``,
  ``DividendReinvestment``, ``DividendReinvestmentResult``.
"""

from __future__ import annotations
