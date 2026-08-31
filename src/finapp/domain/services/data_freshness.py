"""Data freshness policy: decides whether cached data is due for a refresh.

A domain service: pure, stateless logic, no I/O, and no knowledge of BVB
or any other specific data source — usable for any "is this cached thing
stale" decision. ``now`` is passed in explicitly rather than read from the
system clock internally, so this is trivially testable without mocking time.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class DataFreshnessPolicy:
    """Data is due for refresh once at least ``refresh_interval`` has
    elapsed since it was last updated, or if it has never been updated
    (``last_updated is None``)."""

    refresh_interval: timedelta

    def is_due(self, last_updated: datetime | None, now: datetime) -> bool:
        if last_updated is None:
            return True
        return (now - last_updated) >= self.refresh_interval
