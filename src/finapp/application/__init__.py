"""Application layer: use cases and ports (interfaces).

Rules for this package (see ``docs/ARCHITECTURE.md``):

- Depends only on ``finapp.domain``.
- Defines abstract ports (e.g. ``MarketDataProvider``, ``PortfolioRepository``,
  ``ReportExporter``) that the infrastructure layer implements.
- Contains orchestration logic (use cases) but no concrete I/O.

Sprint 1.1 leaves this package empty; use cases and ports are introduced
starting with Sprint 1.3.
"""

from __future__ import annotations
