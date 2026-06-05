"""Cached data-access layer for the Streamlit dashboard.

Pulls the cleaned case data from public.chikungunya_analysis and derives the
helper structures the dashboard needs (long-format symptoms / comorbidities,
epi-week ordering, date filters). All queries are cached so pages are snappy.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Make the pipeline package importable when running `streamlit run app/Home.py`.
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from chikungunya_pipeline.db import get_engine  # noqa: E402
from chikungunya_pipeline.classify import classify_cases  # noqa: E402

DATE_COLS = [
    "date_of_notification", "date_of_sample_taken", "date_of_onset_symptoms",
    "date_attended", "date_of_admission", "date_of_negative_pcr",
]


@st.cache_data(ttl=300, show_spinner="Loading case data …")
def load_cases() -> pd.DataFrame:
    """Load the full case table with parsed dates and a derived case classification."""
    engine = get_engine()
    df = pd.read_sql("SELECT * FROM public.chikungunya_analysis", engine)
    for c in DATE_COLS:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    # WHO/PAHO case classification: prefer the persisted column, derive any gaps
    # (e.g. rows loaded before the column existed).
    try:
        if "case_classification" not in df.columns:
            df["case_classification"] = classify_cases(df)
        else:
            missing = df["case_classification"].isna() | (
                df["case_classification"].astype(str).str.strip() == ""
            )
            if missing.any():
                df.loc[missing, "case_classification"] = classify_cases(df.loc[missing])
    except Exception:
        df["case_classification"] = df.get("case_classification", "Unclassified")
    return df


def explode_multivalue(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Long-format expansion of a '; '-separated column (symptoms/comorbidities)."""
    if column not in df.columns:
        return pd.DataFrame(columns=[column])
    s = (
        df[column]
        .dropna()
        .astype(str)
        .str.split(r"\s*;\s*")
        .explode()
        .str.strip()
    )
    s = s[s.str.len() > 0]
    return s.value_counts().rename_axis(column).reset_index(name="count")


def apply_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """Apply sidebar filters (dict of column -> selected values / date range)."""
    out = df
    for col, sel in filters.items():
        if sel is None or col not in out.columns:
            continue
        if isinstance(sel, tuple) and len(sel) == 2:  # date range
            lo, hi = sel
            out = out[(out[col].isna()) | ((out[col] >= pd.Timestamp(lo)) & (out[col] <= pd.Timestamp(hi)))]
        elif isinstance(sel, (list, set)) and len(sel):
            out = out[out[col].isin(sel)]
    return out


def kpi_summary(df: pd.DataFrame) -> dict:
    """Headline indicators for the overview page."""
    total = len(df)
    pcr_pos = int((df.get("pcr_result") == "Positive").sum()) if "pcr_result" in df else 0
    tested = int(df["pcr_result"].notna().sum()) if "pcr_result" in df else 0
    deaths = int((df.get("outcome") == "Deceased").sum()) if "outcome" in df else 0
    admitted = int((df.get("if_admitted") == "Yes").sum()) if "if_admitted" in df else 0
    return {
        "total_cases": total,
        "pcr_positive": pcr_pos,
        "pcr_positivity_pct": round(100 * pcr_pos / tested, 1) if tested else 0.0,
        "deaths": deaths,
        "cfr_pct": round(100 * deaths / total, 2) if total else 0.0,
        "admitted": admitted,
    }
