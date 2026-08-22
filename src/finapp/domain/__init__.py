"""Domain layer: entities, value objects, and domain services.

Rules for this package (see ``docs/ARCHITECTURE.md``):

- No imports from ``finapp.application``, ``finapp.infrastructure``, or
  ``finapp.presentation``.
- No imports from I/O-oriented third-party libraries (``pandas``,
  ``streamlit``, ``requests``, ``openpyxl``, etc.).
- Monetary values must use :class:`decimal.Decimal`, never ``float``.

Sprint 1.1 established this package as empty scaffolding. Sprint 1.2 added
the core domain model:

- ``finapp.domain.value_objects``: ``Money``, ``Currency``, ``AssetType``.
- ``finapp.domain.entities``: ``Instrument``, ``Position``, ``Portfolio``.
- ``finapp.domain.exceptions``: domain-specific error types.
"""

from __future__ import annotations
