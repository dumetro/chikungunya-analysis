"""Shared sidebar filter widget used across dashboard pages."""

from __future__ import annotations

import pandas as pd
import streamlit as st


def sidebar_filters(df: pd.DataFrame) -> dict:
    """Render sidebar filters and return a filter dict for apply_filters()."""
    st.sidebar.header("Filters")
    filters: dict = {}

    # Onset-date range drives the epi timeline.
    if "date_of_onset_symptoms" in df and df["date_of_onset_symptoms"].notna().any():
        valid = df["date_of_onset_symptoms"].dropna()
        lo, hi = valid.min().date(), valid.max().date()
        rng = st.sidebar.date_input("Onset date range", (lo, hi), min_value=lo, max_value=hi)
        if isinstance(rng, tuple) and len(rng) == 2:
            filters["date_of_onset_symptoms"] = rng

    for col, label in [
        ("health_region", "Health region"),
        ("gender", "Gender"),
        ("local_or_imported", "Local / Imported"),
        ("pcr_result", "PCR result"),
        ("outcome", "Outcome"),
    ]:
        if col in df.columns:
            opts = sorted(df[col].dropna().unique().tolist())
            if opts:
                sel = st.sidebar.multiselect(label, opts, default=[])
                if sel:
                    filters[col] = sel

    return filters
