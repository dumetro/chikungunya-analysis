"""Validate the GX-core wiring on a synthetic DataFrame (no DB required)."""

import datetime as dt

import pandas as pd

from chikungunya_pipeline.validate import validate_dataframe

CFG = {
    "ranges": {"age": {"min": 0, "max": 120}, "gestation_week": {"min": 4, "max": 42}},
    "allowed_sets": {"gender": ["Male", "Female"], "pregnancy": ["Yes", "No"]},
    "date_order": [
        {"later": "date_of_sample_taken", "earlier": "date_of_onset_symptoms"}
    ],
    "conditional_rules": True,
}


def _df():
    return pd.DataFrame(
        {
            "_source_row": [2, 3, 4, 5],
            "age": [30, 200, 45, 10],          # row 3: age out of range
            "gender": ["Male", "Female", "Martian", "Male"],  # row 4: bad gender
            "pregnancy": ["No", "Yes", "No", "No"],
            "gestation_week": [None, 20, None, None],
            "date_of_onset_symptoms": [
                dt.date(2024, 1, 10), dt.date(2024, 1, 10),
                dt.date(2024, 1, 10), dt.date(2024, 1, 20),
            ],
            "date_of_sample_taken": [
                dt.date(2024, 1, 12), dt.date(2024, 1, 12),
                dt.date(2024, 1, 12), dt.date(2024, 1, 5),  # row 5: sample before onset
            ],
        }
    )


def test_validate_splits_pass_fail():
    outcome = validate_dataframe(_df(), CFG)
    failed_rows = set(outcome.failed["_source_row"])
    # rows 3 (age), 4 (gender), 5 (date order) should fail; row 2 passes.
    assert 2 in set(outcome.passed["_source_row"])
    assert {3, 4, 5} <= failed_rows
    assert outcome.n_passed + outcome.n_failed == 4
    assert "reject_reasons" in outcome.failed.columns
    assert outcome.failed.loc[outcome.failed["_source_row"] == 3, "reject_reasons"].iloc[0]
