from pathlib import Path
from typing import Any

import yaml


class Settings:
    """Load configuration from config.yaml."""

    def __init__(self, path: str | Path = "config.yaml") -> None:
        self.path = Path(path)
        self.data: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        with self.path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)
