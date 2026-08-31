from __future__ import annotations

from datetime import UTC, datetime, timedelta

from finapp.domain.services.data_freshness import DataFreshnessPolicy


def test_none_last_updated_is_always_due() -> None:
    policy = DataFreshnessPolicy(refresh_interval=timedelta(hours=1))
    assert policy.is_due(None, datetime.now(UTC)) is True


def test_due_when_interval_elapsed() -> None:
    policy = DataFreshnessPolicy(refresh_interval=timedelta(hours=1))
    now = datetime(2026, 8, 28, 12, 0, tzinfo=UTC)
    last_updated = now - timedelta(hours=2)
    assert policy.is_due(last_updated, now) is True


def test_not_due_when_interval_not_elapsed() -> None:
    policy = DataFreshnessPolicy(refresh_interval=timedelta(hours=1))
    now = datetime(2026, 8, 28, 12, 0, tzinfo=UTC)
    last_updated = now - timedelta(minutes=30)
    assert policy.is_due(last_updated, now) is False


def test_exactly_at_interval_boundary_is_due() -> None:
    policy = DataFreshnessPolicy(refresh_interval=timedelta(hours=1))
    now = datetime(2026, 8, 28, 12, 0, tzinfo=UTC)
    last_updated = now - timedelta(hours=1)
    assert policy.is_due(last_updated, now) is True
