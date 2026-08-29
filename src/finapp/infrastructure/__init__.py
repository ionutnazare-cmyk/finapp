"""Infrastructure layer: adapters implementing application ports.

Rules for this package (see ``docs/ARCHITECTURE.md``):

- May depend on ``finapp.application`` (to implement its ports) and
  ``finapp.domain``.
- Houses concrete I/O: BVB market data clients, file-based repositories,
  Excel/PDF report writers.

Sprint 1.1 established this package as empty scaffolding. Sprint 1.3 added
the first adapters, implementing
:class:`finapp.application.ports.MarketDataProvider`:

- ``finapp.infrastructure.market_data.StaticMarketDataProvider``: in-memory,
  for tests and manual overrides.
- ``finapp.infrastructure.market_data.CsvMarketDataProvider``: reads a local
  CSV cache of quotes in FinApp's own normalized schema.

Sprint 1.4 added portfolio persistence adapters implementing
:class:`finapp.application.ports.PortfolioRepository`:

- ``finapp.infrastructure.repositories.InMemoryPortfolioRepository``: for
  tests and demos.
- ``finapp.infrastructure.repositories.JsonPortfolioRepository``: one JSON
  file per portfolio, written atomically.

Sprint 1.6 added dividend data adapters implementing
:class:`finapp.application.ports.DividendProvider`:

- ``finapp.infrastructure.dividends.StaticDividendProvider``: in-memory,
  for tests and manual overrides.
- ``finapp.infrastructure.dividends.CsvDividendProvider``: reads a local
  CSV cache of dividend payments in FinApp's own normalized schema.

Sprint 1.7 added bonus share issue adapters implementing
:class:`finapp.application.ports.BonusIssueProvider`:

- ``finapp.infrastructure.bonus_issues.StaticBonusIssueProvider``: in-memory,
  for tests and manual overrides.
- ``finapp.infrastructure.bonus_issues.CsvBonusIssueProvider``: reads a
  local CSV cache of bonus issue events in FinApp's own normalized schema.

Sprint 1.14 added report exporters implementing
:class:`finapp.application.ports.PortfolioReportExporter`:

- ``finapp.infrastructure.reporting.ExcelPortfolioReportExporter``: an
  .xlsx workbook (openpyxl) with Summary/Positions/Dividends sheets.
- ``finapp.infrastructure.reporting.PdfPortfolioReportExporter``: a PDF
  document (reportlab) with the same content.

A live BVB data adapter (scraping/fetching real market, dividend, and
corporate-actions data) is scoped for a later sprint.
"""

from __future__ import annotations
