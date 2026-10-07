"""Configuration centralisée, surchargeable par variables d'environnement.

Toutes les variables sont préfixées par ``MEDSQL_`` (ex. ``MEDSQL_MODEL``).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _env(name: str, default: str) -> str:
    return os.environ.get(f"MEDSQL_{name}", default)


@dataclass(frozen=True)
class Settings:
    """Paramètres d'exécution du pipeline."""

    data_dir: Path = field(default_factory=lambda: Path(_env("DATA_DIR", "data")))
    backend: str = field(default_factory=lambda: _env("BACKEND", "ollama"))
    model: str = field(default_factory=lambda: _env("MODEL", "qwen2.5-coder:7b"))
    base_url: str = field(default_factory=lambda: _env("BASE_URL", "http://localhost:11434"))
    api_key: str = field(default_factory=lambda: _env("API_KEY", ""))
    temperature: float = field(default_factory=lambda: float(_env("TEMPERATURE", "0")))
    timeout_s: float = field(default_factory=lambda: float(_env("TIMEOUT", "180")))
    max_rows: int = field(default_factory=lambda: int(_env("MAX_ROWS", "200")))
    query_timeout_s: float = field(default_factory=lambda: float(_env("QUERY_TIMEOUT", "10")))

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "bdpm.sqlite"


def get_settings() -> Settings:
    return Settings()
