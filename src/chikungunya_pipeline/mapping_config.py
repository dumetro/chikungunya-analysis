"""Loader for the Excel column-mapping YAML config."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .config import get_settings


def _norm_header(name: str) -> str:
    """Normalise a header for case/space-insensitive matching."""
    return re.sub(r"\s+", " ", str(name).strip()).lower()


@dataclass
class ColumnMapping:
    sheet: Any = 0
    header_row: int = 0
    columns: dict[str, str] = field(default_factory=dict)  # normalised header -> db col
    date_columns: list[str] = field(default_factory=list)
    integer_columns: list[str] = field(default_factory=list)
    yes_no_columns: list[str] = field(default_factory=list)
    multivalue_columns: dict[str, str] = field(default_factory=dict)  # db col -> entity
    coded_columns: dict[str, str] = field(default_factory=dict)  # db col -> entity
    lookup_columns: dict[str, str] = field(default_factory=dict)  # db col -> lk_category
    value_overrides: dict[str, dict[str, str]] = field(default_factory=dict)
    value_patterns: dict[str, dict[str, str]] = field(default_factory=dict)  # db col -> {regex: canonical}

    def db_column_for(self, excel_header: str) -> str | None:
        return self.columns.get(_norm_header(excel_header))


def load_mapping(path: Path | None = None) -> ColumnMapping:
    """Load and parse the column-mapping YAML."""
    settings = get_settings()
    path = settings.resolve(path or settings.column_mapping_path)
    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    columns = {_norm_header(k): v for k, v in (raw.get("columns") or {}).items()}
    overrides = {
        col: {str(k).strip().lower(): v for k, v in (m or {}).items()}
        for col, m in (raw.get("value_overrides") or {}).items()
    }
    patterns = {
        col: {str(k): v for k, v in (m or {}).items()}
        for col, m in (raw.get("value_patterns") or {}).items()
    }
    return ColumnMapping(
        sheet=raw.get("sheet", 0),
        header_row=raw.get("header_row", 0),
        columns=columns,
        date_columns=list(raw.get("date_columns") or []),
        integer_columns=list(raw.get("integer_columns") or []),
        yes_no_columns=list(raw.get("yes_no_columns") or []),
        multivalue_columns=dict(raw.get("multivalue_columns") or {}),
        coded_columns=dict(raw.get("coded_columns") or {}),
        lookup_columns=dict(raw.get("lookup_columns") or {}),
        value_overrides=overrides,
        value_patterns=patterns,
    )
