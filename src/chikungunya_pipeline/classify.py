"""Derive a chikungunya case classification (Suspected / Probable / Confirmed)
from the cleaned case data, driven by ``config/case_definitions.yaml``.

The classification is computed on the fly from existing columns — it does not
require a new database column. ``classify_cases`` works on a whole DataFrame;
``classify_case`` is a single-record convenience wrapper.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import yaml

from .config import REPO_ROOT

# Matches a canonical age-group label like "20-39" or "60-150".
_AGE_BUCKET_RE = re.compile(r"^\s*(\d+)\s*-\s*(\d+)\s*$")

DEFAULT_PATH = REPO_ROOT / "config" / "case_definitions.yaml"

# Rule keyword -> human label for the resulting tier.
_LABELS = {
    "confirmed": "Confirmed",
    "probable": "Probable",
    "suspected": "Suspected",
    "unclassified": "Unclassified",
}


@lru_cache(maxsize=4)
def load_case_definitions(path: Optional[str] = None) -> dict:
    """Load and cache the case-definitions YAML."""
    p = Path(path) if path else DEFAULT_PATH
    with open(p, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _contains_any(series: pd.Series, terms: list[str]) -> pd.Series:
    low = series.fillna("").astype(str).str.lower()
    if not terms:
        return pd.Series(False, index=series.index)
    return low.apply(lambda t: any(term.lower() in t for term in terms))


def _rule_mask(when: str, signals: dict, index: pd.Index) -> pd.Series:
    """Boolean mask for a classification rule's ``when`` keyword."""
    if when == "pcr_positive":
        return signals["pcr_positive"]
    if when == "clinical_and_epi_link":
        return signals["clinical"] & signals["epi_link"]
    if when == "clinical":
        return signals["clinical"]
    if when == "otherwise":
        return pd.Series(True, index=index)
    # Unknown keyword -> never matches (kept explicit for safety).
    return pd.Series(False, index=index)


def _compute_signals(df: pd.DataFrame, dm: dict) -> dict:
    """Per-row boolean signals used by both classification and reason logging."""
    pcr_col = dm.get("pcr_result_column", "pcr_result")
    epi_col = dm.get("epi_linkage_column", "epi_linkage")
    sym_col = dm.get("symptoms_column", "symptoms")
    pcr_positive_values = {str(v).lower() for v in dm.get("pcr_positive_values", ["Positive"])}
    fever_terms = dm.get("clinical_fever_terms", [])
    arth_terms = dm.get("clinical_arthralgia_terms", [])

    idx = df.index
    false = pd.Series(False, index=idx)
    has_fever = _contains_any(df[sym_col], fever_terms) if sym_col in df else false
    has_arth = _contains_any(df[sym_col], arth_terms) if sym_col in df else false
    return {
        "has_fever": has_fever,
        "has_arth": has_arth,
        "clinical": has_fever & has_arth,
        "pcr_positive": (
            df[pcr_col].fillna("").astype(str).str.lower().isin(pcr_positive_values)
            if pcr_col in df else false
        ),
        "epi_link": (
            df[epi_col].notna() & (df[epi_col].astype(str).str.strip() != "")
            if epi_col in df else false
        ),
        "_pcr_col": pcr_col,
    }


def _labels_from_signals(signals: dict, dm: dict, idx) -> pd.Series:
    rules = dm.get("classification_rules", [{"when": "otherwise", "classify": "unclassified"}])
    conditions = [_rule_mask(r.get("when", ""), signals, idx) for r in rules]
    choices = [_LABELS.get(r.get("classify", "unclassified"), "Unclassified") for r in rules]
    return pd.Series(np.select(conditions, choices, default="Unclassified"), index=idx)


def classify_cases(
    df: pd.DataFrame,
    definitions: Optional[dict] = None,
    scheme: Optional[str] = None,
) -> pd.Series:
    """Return a Series of case classifications for ``df``.

    Rules are evaluated in the order given by ``dataset_mapping.classification_rules``
    in the YAML; the first matching rule wins (priority order).
    """
    definitions = definitions or load_case_definitions()
    dm = definitions.get("dataset_mapping", {})
    return _labels_from_signals(_compute_signals(df, dm), dm, df.index)


def unclassified_reason(signals: dict, i) -> str:
    """Explain why row ``i`` could not be classified (no Confirmed/Suspected match)."""
    parts: list[str] = []
    if not bool(signals["pcr_positive"].at[i]):
        parts.append("not PCR-positive")
    if not bool(signals["clinical"].at[i]):
        missing = []
        if not bool(signals["has_fever"].at[i]):
            missing.append("fever")
        if not bool(signals["has_arth"].at[i]):
            missing.append("arthralgia/arthritis")
        parts.append("clinical criterion not met: symptoms missing " + " & ".join(missing))
    return "; ".join(parts) or "no classifying signal present"


def classify_cases_with_reasons(
    df: pd.DataFrame, definitions: Optional[dict] = None
) -> tuple[pd.Series, pd.Series]:
    """Return (labels, reasons). ``reasons`` is non-empty only for Unclassified rows."""
    definitions = definitions or load_case_definitions()
    dm = definitions.get("dataset_mapping", {})
    signals = _compute_signals(df, dm)
    labels = _labels_from_signals(signals, dm, df.index)
    reasons = pd.Series("", index=df.index, dtype=object)
    for i in df.index[labels == "Unclassified"]:
        reasons.at[i] = unclassified_reason(signals, i)
    return labels, reasons


def classify_case(
    record: dict,
    definitions: Optional[dict] = None,
    scheme: Optional[str] = None,
) -> str:
    """Classify a single case record (dict of column -> value)."""
    series = classify_cases(pd.DataFrame([record]), definitions, scheme)
    return str(series.iloc[0])


# --- Age-group consistency -------------------------------------------------

def _age_group_buckets(allowed: list[str]) -> list[tuple]:
    """Parse canonical 'lo-hi' AGE_GROUP labels into (lo, hi, label), sorted."""
    buckets = []
    for label in allowed or []:
        m = _AGE_BUCKET_RE.match(str(label))
        if m:
            buckets.append((int(m.group(1)), int(m.group(2)), str(label)))
    return sorted(buckets, key=lambda b: b[0])


def age_group_for(age, buckets: list[tuple]) -> Optional[str]:
    """Return the canonical age-group label that ``age`` falls into, or None."""
    if age is None or (isinstance(age, float) and pd.isna(age)):
        return None
    try:
        a = int(float(age))
    except (TypeError, ValueError):
        return None
    for lo, hi, label in buckets:
        if lo <= a <= hi:
            return label
    return None


def fit_age_groups(
    df: pd.DataFrame,
    allowed_age_groups: list[str],
    *,
    age_col: str = "age",
    group_col: str = "age_group",
) -> tuple[pd.DataFrame, list[dict]]:
    """Ensure ``age_group`` matches the canonical AGE_GROUP values.

    For any row whose age_group is missing or not a canonical value, derive the
    correct bucket from ``age`` and overwrite it. Returns (df, lineage records).
    Rows whose age_group is already canonical, or where age is unavailable /
    out of range, are left unchanged.
    """
    records: list[dict] = []
    buckets = _age_group_buckets(allowed_age_groups)
    if group_col not in df.columns or not buckets:
        return df, records
    canonical = {b[2].lower() for b in buckets}
    out = df.copy()
    for i in out.index:
        cur = out.at[i, group_col]
        cur_s = None if cur is None or (isinstance(cur, float) and pd.isna(cur)) else str(cur).strip()
        if cur_s and cur_s.lower() in canonical:
            continue  # already a valid canonical age group
        age = out.at[i, age_col] if age_col in out.columns else None
        new = age_group_for(age, buckets)
        if new and new != cur_s:
            out.at[i, group_col] = new
            records.append({
                "sn": str(out.at[i, "_sn"]) if "_sn" in out.columns else None,
                "source_row": int(out.at[i, "_source_row"]) if "_source_row" in out.columns else None,
                "stage": "derive",
                "column_name": group_col,
                "action": "age_group_from_age",
                "old_value": cur_s,
                "new_value": new,
            })
    return out, records
