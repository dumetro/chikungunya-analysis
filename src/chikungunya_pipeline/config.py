"""Centralised configuration loaded from a ``.env`` file via pydantic-settings.

Every module imports :func:`get_settings` rather than reading the environment
directly, so the connection string, paths and run options live in one place.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root = three levels up from this file (src/chikungunya_pipeline/config.py).
REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime configuration for the pipeline and dashboard."""

    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Required — sourced from DATABASE_URL in the .env file (or the environment).
    # No default: a missing value raises a clear validation error rather than
    # silently connecting to placeholder credentials.
    database_url: str = Field(alias="DATABASE_URL")

    # Required — source workbook used whenever a file is not given explicitly.
    # Sourced from SOURCE_FILE in the .env file (or the environment); no default.
    source_file: Path = Field(alias="SOURCE_FILE")

    incoming_dir: Path = Field(default=Path("data/incoming"), alias="INCOMING_DIR")
    rejects_dir: Path = Field(default=Path("data/rejects"), alias="REJECTS_DIR")
    archive_dir: Path = Field(default=Path("data/archive"), alias="ARCHIVE_DIR")

    column_mapping_path: Path = Field(
        default=Path("config/column_mapping.yaml"), alias="COLUMN_MAPPING_PATH"
    )
    # Offline fallback for analysis_lookups when the DB is unreachable (dry-run).
    lookups_csv: Path = Field(
        default=Path("data/incoming/analysis_lookups.csv"), alias="LOOKUPS_CSV"
    )
    expectations_path: Path = Field(
        default=Path("config/expectations.yaml"), alias="EXPECTATIONS_PATH"
    )

    date_dayfirst: bool = Field(default=True, alias="DATE_DAYFIRST")
    # Force the year of every parsed date (data is known to be one year). None = off.
    data_year: Optional[int] = Field(default=None, alias="DATA_YEAR")
    load_mode: str = Field(default="append", alias="LOAD_MODE")

    def resolve(self, path: Path) -> Path:
        """Resolve a possibly-relative path against the repo root."""
        path = Path(path)
        return path if path.is_absolute() else REPO_ROOT / path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
