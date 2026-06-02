"""Stage 3 — normalise coded columns against reference + raw_map tables.

Design (per the *_raw_map table comments):
    * ``occupation_raw_map(raw_value, occupation_id)``  -> 1:1  whole raw string
    * ``symptom_raw_map(raw_value, symptom_id)``        -> 1:many whole raw string
    * ``comorbidity_raw_map(raw_value, <id>)``          -> 1:many whole raw string
    * ``nationality``                                   -> no raw_map; matched
      directly against the ``nationalities`` reference table by name.

The whole (trimmed, case-folded) source cell is the lookup key. Reference
tables provide the canonical display name. Unmapped values are never dropped:
they are collected (with ``rapidfuzz`` near-match suggestions) so analysts can
extend the maps.

Column names are introspected at runtime so the module tolerates the exact
reference-table DDL: the id column is ``<entity>_id`` and the name column is the
first of {name, <entity>_name, label, title, description} that exists.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd
from rapidfuzz import fuzz, process
from sqlalchemy import Engine, inspect, text

from .db import get_engine

# Candidate name columns, in priority order.
_NAME_CANDIDATES = ("name", "label", "title", "description")


@dataclass
class EntitySpec:
    """Describes how to normalise one entity (occupation, symptom, ...)."""

    entity: str  # e.g. "occupation"
    reference_table: str  # e.g. "occupations"
    raw_map_table: Optional[str]  # e.g. "occupation_raw_map" or None
    multivalue: bool = False  # one raw value -> many canonical names


# The five coded entities in this schema.
ENTITY_SPECS: dict[str, EntitySpec] = {
    "occupation": EntitySpec("occupation", "occupations", "occupation_raw_map"),
    "nationality": EntitySpec("nationality", "nationalities", None),
    "symptom": EntitySpec("symptom", "symptoms", "symptom_raw_map", multivalue=True),
    "comorbidity": EntitySpec(
        "comorbidity", "comorbidities", "comorbidity_raw_map", multivalue=True
    ),
}


@dataclass
class UnmappedReport:
    """Collected unmapped raw values per column, for analyst review."""

    rows: list[dict] = field(default_factory=list)

    def add(self, column: str, raw_value: str, suggestion: str | None, score: float):
        self.rows.append(
            {
                "column": column,
                "raw_value": raw_value,
                "suggested_canonical": suggestion,
                "match_score": round(score, 1),
            }
        )

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows, columns=["column", "raw_value", "suggested_canonical", "match_score"])


def _key(value: str) -> str:
    return " ".join(str(value).split()).lower()


def _detect_columns(engine: Engine, table: str, entity: str) -> tuple[str, str]:
    """Return (id_column, name_column) for a reference table."""
    cols = {c["name"] for c in inspect(engine).get_columns(table)}
    id_col = f"{entity}_id" if f"{entity}_id" in cols else next(
        (c for c in cols if c.endswith("_id")), "id"
    )
    name_col = next(
        (cand for cand in (entity + "_name", *_NAME_CANDIDATES) if cand in cols),
        None,
    )
    if name_col is None:  # fall back to first non-id text-ish column
        name_col = next((c for c in cols if c != id_col), id_col)
    return id_col, name_col


@dataclass
class LookupTables:
    """In-memory lookups built once per pipeline run."""

    # entity -> {raw_key -> [canonical names]}
    raw_to_names: dict[str, dict[str, list[str]]] = field(default_factory=dict)
    # entity -> {name_key -> canonical name} (for direct/fuzzy reference matching)
    canonical_by_key: dict[str, dict[str, str]] = field(default_factory=dict)
    # entity -> list of canonical names (for fuzzy suggestions)
    canonical_names: dict[str, list[str]] = field(default_factory=dict)


def build_lookups(engine: Engine | None = None) -> LookupTables:
    """Load reference + raw_map tables into memory."""
    engine = engine or get_engine()
    lt = LookupTables()

    for spec in ENTITY_SPECS.values():
        id_col, name_col = _detect_columns(engine, spec.reference_table, spec.entity)

        # id -> canonical name
        id_to_name: dict[int, str] = {}
        canonical_key: dict[str, str] = {}
        names: list[str] = []
        with engine.connect() as conn:
            for rid, rname in conn.execute(
                text(f'SELECT {id_col}, {name_col} FROM public.{spec.reference_table}')
            ):
                if rname is None:
                    continue
                id_to_name[rid] = rname
                canonical_key[_key(rname)] = rname
                names.append(rname)
        lt.canonical_by_key[spec.entity] = canonical_key
        lt.canonical_names[spec.entity] = names

        # raw_value -> [names] via raw_map
        raw_to_names: dict[str, list[str]] = {}
        if spec.raw_map_table:
            raw_id_col = f"{spec.entity}_id"
            with engine.connect() as conn:
                try:
                    result = conn.execute(
                        text(
                            f"SELECT raw_value, {raw_id_col} FROM public.{spec.raw_map_table}"
                        )
                    )
                except Exception:
                    result = []
                for raw_value, ref_id in result:
                    if raw_value is None:
                        continue
                    name = id_to_name.get(ref_id)
                    if name is None:
                        continue
                    raw_to_names.setdefault(_key(raw_value), []).append(name)
        lt.raw_to_names[spec.entity] = raw_to_names

    return lt


def _fuzzy_suggest(value: str, candidates: list[str]) -> tuple[str | None, float]:
    if not candidates:
        return None, 0.0
    match = process.extractOne(value, candidates, scorer=fuzz.WRatio)
    if match is None:
        return None, 0.0
    return match[0], float(match[1])


def _normalize_single(
    value: Optional[str], spec: EntitySpec, lt: LookupTables, report: UnmappedReport, column: str
) -> Optional[str]:
    if value is None:
        return None
    key = _key(value)

    # 1) raw_map exact hit.
    names = lt.raw_to_names.get(spec.entity, {}).get(key)
    if names:
        return names[0]
    # 2) direct reference-name hit.
    direct = lt.canonical_by_key.get(spec.entity, {}).get(key)
    if direct:
        return direct
    # 3) unmapped -> suggest + keep original cleaned value.
    suggestion, score = _fuzzy_suggest(value, lt.canonical_names.get(spec.entity, []))
    report.add(column, value, suggestion, score)
    return value


def _normalize_multi(
    value: Optional[str], spec: EntitySpec, lt: LookupTables, report: UnmappedReport, column: str
) -> Optional[str]:
    if value is None:
        return None
    key = _key(value)
    names = lt.raw_to_names.get(spec.entity, {}).get(key)
    if names:
        # canonical, de-duplicated, stable order
        seen, out = set(), []
        for n in names:
            if n not in seen:
                seen.add(n)
                out.append(n)
        return "; ".join(out)
    suggestion, score = _fuzzy_suggest(value, lt.canonical_names.get(spec.entity, []))
    report.add(column, value, suggestion, score)
    return value


def normalize_dataframe(
    df: pd.DataFrame,
    coded_columns: dict[str, str],
    multivalue_columns: dict[str, str],
    lookups: LookupTables | None = None,
) -> tuple[pd.DataFrame, UnmappedReport]:
    """Normalise coded/multivalue columns. Returns (df, unmapped report)."""
    lt = lookups or build_lookups()
    report = UnmappedReport()
    out = df.copy()

    for col, entity in coded_columns.items():
        spec = ENTITY_SPECS.get(entity)
        if spec is None or col not in out.columns:
            continue
        out[col] = out[col].map(lambda v: _normalize_single(v, spec, lt, report, col))

    for col, entity in multivalue_columns.items():
        spec = ENTITY_SPECS.get(entity)
        if spec is None or col not in out.columns:
            continue
        out[col] = out[col].map(lambda v: _normalize_multi(v, spec, lt, report, col))

    return out, report
