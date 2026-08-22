"""Domain value objects: immutable types identified by their value, not identity."""

from __future__ import annotations

from finapp.domain.value_objects.enums import AssetType, Currency
from finapp.domain.value_objects.money import Money

__all__ = ["AssetType", "Currency", "Money"]
