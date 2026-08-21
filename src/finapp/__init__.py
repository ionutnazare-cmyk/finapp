"""FinApp: a dividend investing and retirement optimizer for the BVB.

This package follows Clean Architecture:

- ``finapp.domain``: framework-independent entities and business rules.
- ``finapp.application``: use cases and ports (interfaces).
- ``finapp.infrastructure``: adapters implementing application ports.
- ``finapp.presentation``: CLI and Streamlit dashboard entry points.
"""

from __future__ import annotations

__version__: str = "0.1.0"

__all__ = ["__version__"]
