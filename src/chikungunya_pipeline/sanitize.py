"""Stage 2 — sanitise raw column values with pure, testable functions.

This stage handles *intrinsic* cleaning (whitespace, casing, canonical Yes/No,
numeric coercion, ISO dates). Reference-table normalisation (occupation /
nationality / symptoms / comorbidities) happens later in ``normalize.py``.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

from .dates import to_iso8601
from .mapping_config import ColumnMapping

# Tokens that mean "no value" in free-text string cells.
_NULL_TOKENS = {"", "na", "n/a", "nan", "none", "null", "-", "--", "?"}

_YES_TOKENS = {"yes", "y", "true", "1", "positive", "pos"}
_NO_TOKENS = {"no", "n", "false", "0", "negative", "neg"}

_MALE_TOKENS = {"m", "male", "man", "boy"}
_FEMALE_TOKENS = {"f", "female", "woman", "girl"}


def clean_string(value: object) -> Optional[str]:
    """Trim, collapse internal whitespace; blanks/placeholders -> None."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = " ".join(str(value).split())
    if text.lower() in _NULL_TOKENS:
        return None
    return text or None


def clean_yes_no(value: object) -> Optional[str]:
    """Canonicalise to 'Yes' / 'No' / None (unknown left null)."""
    text = clean_string(value)
    if text is None:
        return None
    low = text.lower()
    if low in _YES_TOKENS:
        return "Yes"
    if low in _NO_TOKENS:
        return "No"
    return None


def clean_gender(value: object) -> Optional[str]:
    text = clean_string(value)
    if text is None:
        return None
    low = text.lower()
    if low in _MALE_TOKENS:
        return "Male"
    if low in _FEMALE_TOKENS:
        return "Female"
    return None


def clean_int(value: object, *, lo: int | None = None, hi: int | None = None) -> Optional[int]:
    """Coerce to int; values outside [lo, hi] become None (caught later)."""
    text = clean_string(value)
    if text is None:
        return None
    try:
        num = int(round(float(text)))
    except (ValueError, TypeError):
        return None
    if lo is not None and num < lo:
        return None
    if hi is not None and num > hi:
        return None
    return num


def apply_overrides(value: Optional[str], overrides: dict[str, str]) -> Optional[str]:
    if value is None:
        return None
    return overrides.get(value.strip().lower(), value)


def sanitize_dataframe(df: pd.DataFrame, mapping: ColumnMapping) -> pd.DataFrame:
    """Return a sanitised copy of the ingested DataFrame.

    Cross-field rule applied here: gestation_week is cleared when pregnancy is
    not 'Yes' (mirrors the DB CHECK constraint chk_gestation_only_if_pregnant).
    """
    out = df.copy()
    date_cols = set(mapping.date_columns)
    int_cols = set(mapping.integer_columns)
    yn_cols = set(mapping.yes_no_columns)

    for col in out.columns:
        if col == "_source_row":
            continue
        if col in date_cols:
            out[col] = out[col].map(lambda v: to_iso8601(v))
        elif col == "age":
            out[col] = out[col].map(lambda v: clean_int(v, lo=0, hi=120))
        elif col == "gestation_week":
            out[col] = out[col].map(lambda v: clean_int(v, lo=4, hi=42))
        elif col in int_cols:
            out[col] = out[col].map(clean_int)
        elif col in yn_cols:
            out[col] = out[col].map(clean_yes_no)
        elif col == "gender":
            out[col] = out[col].map(clean_gender)
        else:
            out[col] = out[col].map(clean_string)

        # Per-column literal overrides from config.
        if col in mapping.value_overrides:
            ov = mapping.value_overrides[col]
            out[col] = out[col].map(lambda v: apply_overrides(v, ov))

    # Gestation only valid when pregnant. Use object dtype so the cleared cells
    # are real None (not NaN), which load.py needs for SQL NULLs.
    if "gestation_week" in out.columns and "pregnancy" in out.columns:
        out["gestation_week"] = out["gestation_week"].astype(object)
        out.loc[out["pregnancy"] != "Yes", "gestation_week"] = None

    # Normalise every NaN / NaT to None for clean SQL NULLs downstream.
    out = out.astype(object)
    out = out.where(out.notna(), None)
    return out
