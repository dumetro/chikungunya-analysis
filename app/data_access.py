"""Cached data-access layer for the Streamlit dashboard.

Pulls the cleaned case data from public.chikungunya_analysis and derives the
helper structures the dashboard needs (long-format symptoms / comorbidities,
epi-week ordering, date filters). All queries are cached so pages are snappy.
"""

from __future__ import annotations

import re
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

# MoH health region -> Mauritius district (matches the `province` field in
# data/geodata/mauritius_adm1.json). Single source of truth for the geographic
# and attack-rate views. Regions 6-8 are not yet present in the case data.
REGION_TO_DISTRICT = {
    "Region 1": "PORT LOUIS", "Region 2": "PAMPLEMOUSSES",
    "Region 3": "RIVIÈRE DU REMPART", "Region 4": "FLACQ",
    "Region 5": "GRAND PORT", "Region 6": "SAVANNE",
    "Region 7": "BLACK RIVER", "Region 8": "PLAINES WILHEMS",
}

# District resident population (for attack-rate denominators), keyed to the
# district names above.
DISTRICT_POPULATION = {
    "PORT LOUIS": 108_594, "PAMPLEMOUSSES": 141_696,
    "RIVIÈRE DU REMPART": 110_756, "FLACQ": 138_156,
    "GRAND PORT": 111_092, "SAVANNE": 67_284,
    "PLAINES WILHEMS": 347_589, "MOKA": 85_614, "BLACK RIVER": 89_053,
}

# National population by the analysis age bands, aggregated from World Bank 2023
# 5-year bands (data/popdata/mau_population.csv): 0-19 = 0-4…15-19, etc.
# Keyed to the canonical AGE_GROUP labels ("60-150" = 60+). Note this is 2023 and
# national, whereas DISTRICT_POPULATION is 2020 — they intentionally differ.
AGE_GROUP_POPULATION = {
    "0-19": 279_052, "20-39": 387_843, "40-59": 352_812, "60-150": 241_337,
}


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


@st.cache_data(ttl=120, show_spinner=False)
def load_transformations() -> pd.DataFrame:
    """Load the data-lineage audit log (empty frame if the table is absent)."""
    try:
        return pd.read_sql(
            "SELECT run_id, source_file, sn, source_row, stage, column_name, "
            "action, old_value, new_value, applied_at "
            "FROM public.pipeline_transformations ORDER BY id DESC",
            get_engine(),
        )
    except Exception:
        return pd.DataFrame(
            columns=["run_id", "source_file", "sn", "source_row", "stage",
                     "column_name", "action", "old_value", "new_value", "applied_at"]
        )


def parse_epi_week(value) -> "int | None":
    """Extract the integer epi week from a messy epi_week string.

    Handles "11", "W11", "Week 11", "2024-W14" -> 11/11/11/14.
    """
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    m = re.search(r"[Ww]\s*0*(\d{1,2})", s)        # ...W14
    if not m:
        m = re.search(r"\b0*(\d{1,2})\b", s)        # bare week number
    if not m:
        return None
    wk = int(m.group(1))
    return wk if 1 <= wk <= 53 else None


def epi_week_counts(df: pd.DataFrame) -> pd.DataFrame:
    """Cases per epi week as a continuous series from the min to the max
    observed week (zero-filled), so the curve always extends to max(epi_week)."""
    if "epi_week" not in df.columns:
        return pd.DataFrame(columns=["epi_week", "cases"])
    weeks = df["epi_week"].map(parse_epi_week).dropna().astype(int)
    if weeks.empty:
        return pd.DataFrame(columns=["epi_week", "cases"])
    counts = weeks.value_counts().sort_index()
    full = range(int(counts.index.min()), int(counts.index.max()) + 1)
    counts = counts.reindex(full, fill_value=0)
    return pd.DataFrame({"epi_week": list(counts.index), "cases": counts.values})


def epi_week_classification_counts(df: pd.DataFrame) -> pd.DataFrame:
    """Per-epi-week Confirmed vs Suspected counts (long format), zero-filled to a
    continuous week range.

    Confirmed = case_classification == 'Confirmed'. Suspected = everything else
    (i.e. anything not yet confirmed is treated as suspected). The two segments
    sum to the weekly total.
    """
    empty = pd.DataFrame(columns=["epi_week", "Classification", "cases"])
    if "epi_week" not in df.columns:
        return empty
    d = df.copy()
    d["_wk"] = d["epi_week"].map(parse_epi_week)
    d = d.dropna(subset=["_wk"])
    if d.empty:
        return empty
    d["_wk"] = d["_wk"].astype(int)
    confirmed = d.get("case_classification", pd.Series(index=d.index)) == "Confirmed"
    d["Classification"] = ["Confirmed" if c else "Suspected" for c in confirmed]

    wide = (d.groupby(["_wk", "Classification"]).size()
            .unstack(fill_value=0))
    for col in ("Suspected", "Confirmed"):
        if col not in wide.columns:
            wide[col] = 0
    full = range(int(d["_wk"].min()), int(d["_wk"].max()) + 1)
    wide = wide.reindex(full, fill_value=0)[["Suspected", "Confirmed"]]
    long = (wide.reset_index(names="epi_week")
            .melt(id_vars="epi_week", var_name="Classification", value_name="cases"))
    return long


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
