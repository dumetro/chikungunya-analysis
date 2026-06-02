"""Unit tests for analysis_lookups normalisation (offline, via the seed CSV)."""

import pandas as pd

from chikungunya_pipeline.normalize import load_lookup_sets, normalize_dataframe

LOOKUP_COLUMNS = {
    "pcr_result": "PCR_RESULT",
    "outcome": "OUTCOME",
    "active_passive": "ACTIVE_PASSIVE",
    "age_group": "AGE_GROUP",
}
PATTERNS = {
    "pcr_result": {r"\bpos": "Positive", r"\bneg": "Negative"},
    "age_group": {r"60.*above": "60-150"},
}
OVERRIDES = {"age_group": {"60 and above": "60-150"}}


def test_lookup_sets_loaded_from_csv():
    ls = load_lookup_sets()  # DB unavailable in tests -> CSV fallback
    assert "Positive" in ls.allowed("PCR_RESULT")
    assert "Passive" in ls.allowed("ACTIVE_PASSIVE")


def test_lookup_normalization_cases_patterns_overrides():
    df = pd.DataFrame(
        {
            "_source_row": [2, 3, 4, 5, 6, 7],
            "pcr_result": ["POSITIVE", "POS ON 11.5.2026", "poSITIVE", "NIL", "neg", "POSITVE"],
            "active_passive": ["PASSIVE", "passive", "ACTIVE", "HOME ISOLATION", "Active", "UNR"],
            "outcome": ["Discharged", "DISCHARGED", "Active", "alive", "deceased", "x"],
            "age_group": ["0-19", "60 and above", "60 AND ABOVE", "40-59", "20-39", "0-19"],
        }
    )
    out, report = normalize_dataframe(
        df, {}, {}, lookup_columns=LOOKUP_COLUMNS,
        value_overrides=OVERRIDES, value_patterns=PATTERNS,
    )
    # case-insensitive exact + patterns
    assert out["pcr_result"].tolist()[:3] == ["Positive", "Positive", "Positive"]
    assert out.loc[out["_source_row"] == 6, "pcr_result"].iloc[0] == "Negative"  # neg pattern
    assert out.loc[out["_source_row"] == 7, "pcr_result"].iloc[0] == "Positive"  # POSITVE typo via \bpos
    assert out["active_passive"].tolist()[:3] == ["Passive", "Passive", "Active"]
    # override + pattern for age group
    assert out["age_group"].tolist() == ["0-19", "60-150", "60-150", "40-59", "20-39", "0-19"]
    # genuinely unmapped values are kept raw and reported
    assert "NIL" in out["pcr_result"].tolist()
    assert any(r["raw_value"] == "NIL" for r in report.rows)
    assert any(r["raw_value"] == "HOME ISOLATION" for r in report.rows)
