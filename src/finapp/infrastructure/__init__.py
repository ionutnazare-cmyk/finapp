"""Infrastructure layer: adapters implementing application ports.

Rules for this package (see ``docs/ARCHITECTURE.md``):

- May depend on ``finapp.application`` (to implement its ports) and
  ``finapp.domain``.
- Houses concrete I/O: BVB market data clients, file-based repositories,
  Excel/PDF report writers.

Sprint 1.1 leaves this package empty; the first adapter (a BVB market data
provider) is scoped for Sprint 1.3.
"""

from __future__ import annotations
