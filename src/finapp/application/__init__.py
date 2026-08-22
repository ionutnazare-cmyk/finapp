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

Use cases (orchestration logic that calls ports and domain entities
together) are introduced starting with Sprint 1.4.
"""

from __future__ import annotations
