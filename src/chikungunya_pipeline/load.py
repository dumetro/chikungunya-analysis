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

import pandas as pd
from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Engine,
    Float,
    Integer,
    Numeric,
    SmallInteger,
    inspect,
    text,
)

from .db import get_engine

TARGET_TABLE = "chikungunya_analysis"
LOG_TABLE = "pipeline_load_log"

# Columns that are never written from source data.
_NON_SOURCE = {"id", "created_at", "updated_at", "_source_row", "_sn",
               "reject_reasons", "failed_columns"}

# Pipeline-derived columns: written to the DB, but excluded from the idempotency
# hash so re-deriving them never changes a row's identity.
_DERIVED = {"case_classification"}

# Idempotently ensure pipeline-managed columns exist before loading.
_ENSURE_COLUMNS = (
    f"ALTER TABLE public.{TARGET_TABLE} "
    "ADD COLUMN IF NOT EXISTS case_classification varchar(20)",
)

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
    n_failed: int = 0
    failures: "pd.DataFrame | None" = None  # failed rows + 'load_error' column
    n_log_reconciled: int = 0  # stale idempotency-log hashes cleared before load


def _target_columns(engine: Engine) -> list[str]:
    cols = [c["name"] for c in inspect(engine).get_columns(TARGET_TABLE)]
    return [c for c in cols if c not in _NON_SOURCE]


def column_max_lengths(engine: Engine | None = None, table: str = TARGET_TABLE) -> dict[str, int]:
    """Return {column: max_length} for VARCHAR/CHAR columns of a table.

    Used by validation to reject over-length values before they reach the DB.
    """
    engine = engine or get_engine()
    out: dict[str, int] = {}
    for col in inspect(engine).get_columns(table):
        length = getattr(col.get("type"), "length", None)
        if isinstance(length, int) and length > 0:
            out[col["name"]] = length
    return out


def _column_kind(sa_type) -> tuple[str, "int | None", "int | None"]:
    """Map a SQLAlchemy column type to (kind, min, max) for validation."""
    if isinstance(sa_type, Boolean):
        return "bool", None, None
    if isinstance(sa_type, SmallInteger):
        return "int", -32768, 32767
    if isinstance(sa_type, BigInteger):
        return "int", None, None
    if isinstance(sa_type, Integer):
        return "int", -2147483648, 2147483647
    if isinstance(sa_type, (Date, DateTime)):
        return "date", None, None
    if isinstance(sa_type, (Numeric, Float)):
        return "float", None, None
    return "str", None, None


def target_schema(engine: Engine | None = None, table: str = TARGET_TABLE) -> dict[str, dict]:
    """Introspect the target table into per-column specs for validation.

    Returns {column: {kind, length, nullable, min, max}} for every source
    column, so validation can enforce the source data against the actual DB
    schema (type, nullability, varchar length, integer range) before load.
    """
    engine = engine or get_engine()
    specs: dict[str, dict] = {}
    for col in inspect(engine).get_columns(table):
        name = col["name"]
        if name in _NON_SOURCE:
            continue
        kind, mn, mx = _column_kind(col.get("type"))
        length = getattr(col.get("type"), "length", None)
        specs[name] = {
            "kind": kind,
            "length": length if isinstance(length, int) else None,
            "nullable": bool(col.get("nullable", True)),
            "min": mn,
            "max": mx,
        }
    return specs


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
    # Ensure derived columns exist, then introspect so they're picked up.
    with engine.begin() as conn:
        for stmt in _ENSURE_COLUMNS:
            conn.execute(text(stmt))
    columns = _target_columns(engine)
    insert_cols = [c for c in columns if c in df.columns]
    hash_columns = [c for c in columns if c not in _DERIVED]
    reconciled = 0

    with engine.begin() as conn:
        conn.execute(text(_CREATE_LOG))
        if mode == "replace":
            conn.execute(text(f"TRUNCATE TABLE public.{TARGET_TABLE} RESTART IDENTITY CASCADE"))
            conn.execute(text(f"TRUNCATE TABLE public.{LOG_TABLE}"))
        else:
            # Self-heal a stale idempotency log. The log and the target table are
            # only guaranteed consistent when both are truncated together (replace
            # mode). If the table was emptied out-of-band (manual TRUNCATE/DELETE,
            # or a DROP+recreate from the DDL scripts) the log's hashes survive and
            # would wrongly mark every incoming row a duplicate — silently skipping
            # the whole load. An empty table can hold no duplicates, so any leftover
            # hashes are stale: clear them so append mode reloads cleanly.
            n_target = conn.execute(
                text(f"SELECT count(*) FROM public.{TARGET_TABLE}")
            ).scalar()
            n_log = conn.execute(
                text(f"SELECT count(*) FROM public.{LOG_TABLE}")
            ).scalar()
            if n_target == 0 and n_log:
                conn.execute(text(f"TRUNCATE TABLE public.{LOG_TABLE}"))
                reconciled = int(n_log)

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
        failures: list[dict] = []
        for record in df.to_dict(orient="records"):
            h = _row_hash(record, hash_columns)
            if h in existing:
                skipped += 1
                continue
            params = {c: record.get(c) for c in insert_cols}
            try:
                # Per-row savepoint: a bad row rolls back only itself, so one
                # failure never aborts the whole batch.
                with conn.begin_nested():
                    conn.execute(insert_sql, params)
                    conn.execute(
                        log_sql,
                        {"h": h, "f": source_file, "r": int(record.get("_source_row") or 0)},
                    )
                existing.add(h)
                inserted += 1
            except Exception as exc:  # capture & quarantine the row, keep going
                reason = str(getattr(exc, "orig", exc)).splitlines()[0].strip()
                failures.append({**record, "load_error": reason})

    failures_df = pd.DataFrame(failures) if failures else None
    return LoadResult(
        n_candidate=len(df),
        n_inserted=inserted,
        n_skipped_duplicate=skipped,
        source_file=source_file,
        n_failed=len(failures),
        failures=failures_df,
        n_log_reconciled=reconciled,
    )
