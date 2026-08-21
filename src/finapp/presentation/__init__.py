"""Presentation layer: CLI and Streamlit dashboard entry points.

Rules for this package (see ``docs/ARCHITECTURE.md``):

- May depend on ``finapp.application``, ``finapp.infrastructure``, and
  ``finapp.domain``.
- Wires use cases to user input/output; contains no business logic itself.
"""

from __future__ import annotations
