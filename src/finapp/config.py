"""Application-wide, environment-driven configuration.

Sprint 1.1 defines the settings surface only; later sprints will consume these
values from the infrastructure and presentation layers (e.g. to locate BVB
data caches or select the reporting currency).
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    """Deployment environment for the running application."""

    LOCAL = "local"
    TEST = "test"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Central application settings, loaded from environment variables or `.env`.

    All FinApp-specific variables are prefixed with ``FINAPP_``, e.g.
    ``FINAPP_BASE_CURRENCY``.
    """

    model_config = SettingsConfigDict(
        env_prefix="FINAPP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    environment: Environment = Field(default=Environment.LOCAL)
    base_currency: str = Field(default="RON", min_length=3, max_length=3)
    data_dir: Path = Field(default=Path("./data"))


def get_settings() -> Settings:
    """Return a freshly loaded :class:`Settings` instance.

    A function (rather than a module-level singleton) keeps configuration
    loading explicit and easily overridable in tests.
    """

    return Settings()
