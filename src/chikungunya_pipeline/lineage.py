"""Data-lineage tracking: row-level corrections + normalization provenance.

Transformations are recorded as append-only events in the
``pipeline_transformations`` audit table (one row per change), keyed by the
source SN, so a lineage report can be generated per row / column / action.

Captured (per the chosen scope):
  * explicit SN-keyed corrections from config/corrections.yaml (move/clear/set)
  * reference/lookup normalisations (raw -> canonical), via frame diffing.
Low-level whitespace/case cleanups (the sanitise stage) are intentionally
not logged.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd
import yaml
from sqlalchemy import Engine, text

from .config import REPO_ROOT, get_settings
from .db import get_engine

TRANSFORM_TABLE = "pipeline_transformations"
DEFAULT_CORRECTIONS = REPO_ROOT / "config" / "corrections.yaml"

_CREATE_TABLE = f"""
CREATE TABLE IF NOT EXISTS public.{TRANSFORM_TABLE} (
    id          bigserial PRIMARY KEY,
    run_id      text NOT NULL,
    source_file text,
    sn          text,
    source_row  integer,
    stage       text NOT NULL,
    column_name text,
    action      text NOT NULL,
    old_value   text,
    new_value   text,
    applied_at  timestamptz NOT NULL DEFAULT now()
)
"""

_INDEXES = (
    f"CREATE INDEX IF NOT EXISTS idx_pt_sn ON public.{TRANSFORM_TABLE} (sn)",
    f"CREATE INDEX IF NOT EXISTS idx_pt_column ON public.{TRANSFORM_TABLE} (column_name)",
    f"CREATE INDEX IF NOT EXISTS idx_pt_run ON public.{TRANSFORM_TABLE} (run_id)",
    f"CREATE INDEX IF NOT EXISTS idx_pt_action ON public.{TRANSFORM_TABLE} (action)",
)


def _to_str(v) -> Optional[str]:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, str):
        return v
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return str(v)


def _event(row, *, stage, column, action, old, new) -> dict:
    return {
        "sn": _to_str(row.get("_sn")),
        "source_row": int(row.get("_source_row")) if row.get("_source_row") is not None else None,
        "stage": stage,
        "column_name": column,
        "action": action,
        "old_value": _to_str(old),
        "new_value": _to_str(new),
    }


# --- Corrections -----------------------------------------------------------

def load_corrections(path: Optional[Path] = None) -> dict:
    """Load the SN-keyed corrections config (str SN -> list of action dicts)."""
    p = Path(path) if path else DEFAULT_CORRECTIONS
    if not p.exists():
        return {}
    data = yaml.safe_load(open(p, "r", encoding="utf-8")) or {}
    return {str(k): (v or []) for k, v in (data.get("corrections") or {}).items()}


def _apply_one(row: dict, action: dict, records: list[dict]) -> None:
    kind = action.get("action")
    if kind == "move":
        src, dst = action.get("from"), action.get("to")
        val = row.get(src)
        if val in (None, "") or src not in row or dst not in row:
            return
        target_old = row.get(dst)
        new_target = val if target_old in (None, "") else f"{target_old}; {val}"
        row[dst] = new_target
        row[src] = None
        records.append(_event(row, stage="correction", column=dst,
                              action=f"move_in<-{src}", old=target_old, new=new_target))
        records.append(_event(row, stage="correction", column=src,
                              action=f"move_out->{dst}", old=val, new=None))
    elif kind == "clear":
        col = action.get("column")
        if col in row and row.get(col) not in (None, ""):
            old = row.get(col)
            row[col] = None
            records.append(_event(row, stage="correction", column=col,
                                  action="clear", old=old, new=None))
    elif kind == "set":
        col, value = action.get("column"), action.get("value")
        if col in row:
            old = row.get(col)
            row[col] = value
            records.append(_event(row, stage="correction", column=col,
                                  action="set", old=old, new=value))


def apply_corrections(
    df: pd.DataFrame, corrections: Optional[dict] = None
) -> tuple[pd.DataFrame, list[dict]]:
    """Apply SN-keyed corrections, returning (corrected df, transformation records)."""
    corrections = corrections if corrections is not None else load_corrections()
    if not corrections or "_sn" not in df.columns:
        return df, []
    out = df.copy()
    records: list[dict] = []
    sn_str = out["_sn"].map(_to_str)
    for sn, actions in corrections.items():
        idx = out.index[sn_str == str(sn)]
        for i in idx:
            row = out.loc[i].to_dict()
            for action in actions:
                _apply_one(row, action, records)
            out.loc[i] = pd.Series(row)
    return out, records


# --- Normalisation diff ----------------------------------------------------

def diff_records(
    before: pd.DataFrame,
    after: pd.DataFrame,
    *,
    stage: str,
    action: str,
    columns: list[str],
) -> list[dict]:
    """Record cells that changed between two frames (same index) for ``columns``."""
    records: list[dict] = []
    cols = [c for c in columns if c in before.columns and c in after.columns]
    for i in after.index:
        for c in cols:
            old, new = before.at[i, c], after.at[i, c]
            o, n = _to_str(old), _to_str(new)
            if o != n:
                records.append({
                    "sn": _to_str(after.at[i, "_sn"]) if "_sn" in after.columns else None,
                    "source_row": int(after.at[i, "_source_row"]) if "_source_row" in after.columns else None,
                    "stage": stage,
                    "column_name": c,
                    "action": action,
                    "old_value": o,
                    "new_value": n,
                })
    return records


# --- Persistence -----------------------------------------------------------

def ensure_table(engine: Engine | None = None) -> None:
    engine = engine or get_engine()
    with engine.begin() as conn:
        conn.execute(text(_CREATE_TABLE))
        for stmt in _INDEXES:
            conn.execute(text(stmt))


def write_transformations(
    records: list[dict], *, run_id: str, source_file: str, engine: Engine | None = None
) -> int:
    """Persist transformation events to the audit table. Returns rows written."""
    if not records:
        return 0
    engine = engine or get_engine()
    ensure_table(engine)
    sql = text(
        f"INSERT INTO public.{TRANSFORM_TABLE} "
        "(run_id, source_file, sn, source_row, stage, column_name, action, old_value, new_value) "
        "VALUES (:run_id, :source_file, :sn, :source_row, :stage, :column_name, "
        ":action, :old_value, :new_value)"
    )
    payload = [{**r, "run_id": run_id, "source_file": source_file} for r in records]
    with engine.begin() as conn:
        conn.execute(sql, payload)
    return len(payload)


def records_to_frame(records: list[dict], *, run_id: str, source_file: str) -> pd.DataFrame:
    cols = ["run_id", "source_file", "sn", "source_row", "stage",
            "column_name", "action", "old_value", "new_value"]
    rows = [{**r, "run_id": run_id, "source_file": source_file} for r in records]
    return pd.DataFrame(rows, columns=cols)
