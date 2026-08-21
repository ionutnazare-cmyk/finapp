"""Domain layer: entities, value objects, and domain services.

Rules for this package (see ``docs/ARCHITECTURE.md``):

- No imports from ``finapp.application``, ``finapp.infrastructure``, or
  ``finapp.presentation``.
- No imports from I/O-oriented third-party libraries (``pandas``,
  ``streamlit``, ``requests``, ``openpyxl``, etc.).
- Monetary values must use :class:`decimal.Decimal`, never ``float``.

Sprint 1.1 intentionally leaves this package empty of business logic; the
core domain model (``Instrument``, ``Position``, ``Portfolio``, ``Money``)
is scoped for Sprint 1.2.
"""

from __future__ import annotations
