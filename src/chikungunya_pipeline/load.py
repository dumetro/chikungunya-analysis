"""Stage 5 — load validated rows into public.chikungunya_analysis.

Idempotency: a SHA-256 hash of each row's business columns is recorded in a
small ``pipeline_load_log`` table; rows whose hash is already present are
skipped, so re-running a file never double-inserts. The insert runs in a single
transaction (all-or-nothing).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import Engine, inspect, text

from .db import get_engine

TARGET_TABLE = "chikungunya_analysis"
LOG_TABLE = "pipeline_load_log"

# Columns that are never written from source data.
_NON_SOURCE = {"id", "created_at", "updated_at", "_source_row", "reject_reasons"}

_CREATE_LOG = f"""
CREATE TABLE IF NOT EXISTS public.{LOG_TABLE} (
    load_hash  text PRIMARY KEY,
    source_file text,
    source_row  integer,
    loaded_at   timestamptz NOT NULL DEFAULT now()
)
"""


@dataclass
class LoadResult:
    n_candidate: int
    n_inserted: int
    n_skipped_duplicate: int
    source_file: str


def _target_columns(engine: Engine) -> list[str]:
    cols = [c["name"] for c in inspect(engine).get_columns(TARGET_TABLE)]
    return [c for c in cols if c not in _NON_SOURCE]


def _row_hash(row: dict, columns: list[str]) -> str:
    payload = {c: (row.get(c).isoformat() if hasattr(row.get(c), "isoformat") else row.get(c))
               for c in columns}
    blob = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def load_dataframe(
    df: pd.DataFrame,
    source_file: str,
    *,
    mode: str = "append",
    engine: Engine | None = None,
) -> LoadResult:
    """Insert validated rows. mode='replace' truncates the table first."""
    engine = engine or get_engine()
    columns = _target_columns(engine)
    insert_cols = [c for c in columns if c in df.columns]

    with engine.begin() as conn:
        conn.execute(text(_CREATE_LOG))
        if mode == "replace":
            conn.execute(text(f"TRUNCATE TABLE public.{TARGET_TABLE} RESTART IDENTITY CASCADE"))
            conn.execute(text(f"TRUNCATE TABLE public.{LOG_TABLE}"))

        existing = {
            r[0] for r in conn.execute(text(f"SELECT load_hash FROM public.{LOG_TABLE}"))
        }

        col_list = ", ".join(insert_cols)
        placeholders = ", ".join(f":{c}" for c in insert_cols)
        insert_sql = text(
            f"INSERT INTO public.{TARGET_TABLE} ({col_list}) VALUES ({placeholders})"
        )
        log_sql = text(
            f"INSERT INTO public.{LOG_TABLE} (load_hash, source_file, source_row) "
            f"VALUES (:h, :f, :r)"
        )

        inserted = skipped = 0
        now = datetime.now(timezone.utc)
        for record in df.to_dict(orient="records"):
            h = _row_hash(record, columns)
            if h in existing:
                skipped += 1
                continue
            params = {c: record.get(c) for c in insert_cols}
            conn.execute(insert_sql, params)
            conn.execute(
                log_sql, {"h": h, "f": source_file, "r": int(record.get("_source_row") or 0)}
            )
            existing.add(h)
            inserted += 1

    return LoadResult(
        n_candidate=len(df),
        n_inserted=inserted,
        n_skipped_duplicate=skipped,
        source_file=source_file,
    )
