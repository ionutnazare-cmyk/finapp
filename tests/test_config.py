from __future__ import annotations

from pathlib import Path

import pytest

from finapp.config import Environment, Settings, get_settings


def test_default_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FINAPP_ENVIRONMENT", raising=False)
    monkeypatch.delenv("FINAPP_BASE_CURRENCY", raising=False)
    monkeypatch.delenv("FINAPP_DATA_DIR", raising=False)

    settings = get_settings()

    assert settings.environment == Environment.LOCAL
    assert settings.base_currency == "RON"
    assert settings.data_dir == Path("./data")


def test_settings_are_frozen() -> None:
    settings = Settings()
    with pytest.raises(Exception):  # noqa: B017 - pydantic raises its own error type
        settings.base_currency = "USD"  # type: ignore[misc]


def test_settings_read_environment_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FINAPP_ENVIRONMENT", "test")
    monkeypatch.setenv("FINAPP_BASE_CURRENCY", "USD")

    settings = get_settings()

    assert settings.environment == Environment.TEST
    assert settings.base_currency == "USD"
