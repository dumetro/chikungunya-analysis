"""Stage 1 — read the source Excel file into a raw DataFrame.

Headers are renamed to DB column names using the mapping config. Unmapped
columns are dropped (and reported). A ``_source_row`` column preserves the
original 1-based Excel row number so any reject can be traced back.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .mapping_config import ColumnMapping, _norm_header, load_mapping


@dataclass
class IngestResult:
    df: pd.DataFrame
    mapped_headers: dict[str, str]
    unmapped_headers: list[str]
    source_path: Path


def read_excel(path: str | Path, mapping: ColumnMapping | None = None) -> IngestResult:
    """Read an Excel file and rename columns to DB column names."""
    mapping = mapping or load_mapping()
    path = Path(path)

    raw = pd.read_excel(
        path,
        sheet_name=mapping.sheet,
        header=mapping.header_row,
        dtype=object,  # keep everything as-is; cleaning happens in sanitize.
    )

    mapped: dict[str, str] = {}
    unmapped: list[str] = []
    rename: dict[str, str] = {}
    for col in raw.columns:
        db_col = mapping.columns.get(_norm_header(col))
        if db_col:
            rename[col] = db_col
            mapped[str(col)] = db_col
        else:
            unmapped.append(str(col))

    df = raw.rename(columns=rename)
    # Keep only mapped DB columns (dedupe if two headers map to the same column).
    keep = [c for c in df.columns if c in set(rename.values())]
    df = df.loc[:, ~df.columns.duplicated()][keep].copy()

    # 1-based Excel row number (header is at header_row, data starts after).
    df.insert(0, "_source_row", range(mapping.header_row + 2, mapping.header_row + 2 + len(df)))

    return IngestResult(
        df=df,
        mapped_headers=mapped,
        unmapped_headers=unmapped,
        source_path=path,
    )
