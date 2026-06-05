"""Derive a chikungunya case classification (Suspected / Probable / Confirmed)
from the cleaned case data, driven by ``config/case_definitions.yaml``.

The classification is computed on the fly from existing columns — it does not
require a new database column. ``classify_cases`` works on a whole DataFrame;
``classify_case`` is a single-record convenience wrapper.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import yaml

from .config import REPO_ROOT

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
    rules = dm.get("classification_rules", [{"when": "otherwise", "classify": "unclassified"}])

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
    signals = {
        "clinical": has_fever & has_arth,
        "pcr_positive": (
            df[pcr_col].fillna("").astype(str).str.lower().isin(pcr_positive_values)
            if pcr_col in df else false
        ),
        "epi_link": (
            df[epi_col].notna() & (df[epi_col].astype(str).str.strip() != "")
            if epi_col in df else false
        ),
    }

    conditions = [_rule_mask(r.get("when", ""), signals, idx) for r in rules]
    choices = [_LABELS.get(r.get("classify", "unclassified"), "Unclassified") for r in rules]
    return pd.Series(np.select(conditions, choices, default="Unclassified"), index=idx)


def classify_case(
    record: dict,
    definitions: Optional[dict] = None,
    scheme: Optional[str] = None,
) -> str:
    """Classify a single case record (dict of column -> value)."""
    series = classify_cases(pd.DataFrame([record]), definitions, scheme)
    return str(series.iloc[0])
