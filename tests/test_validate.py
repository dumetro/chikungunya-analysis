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


def test_max_length_rejects_overlong_values():
    df = pd.DataFrame(
        {
            "_source_row": [2, 3],
            "age": [30, 40],
            "dmu_hospitalised_tba_missing": ["SHORT", "X" * 60],
        }
    )
    outcome = validate_dataframe(df, {"conditional_rules": True},
                                 max_lengths={"dmu_hospitalised_tba_missing": 50})
    assert set(outcome.passed["_source_row"]) == {2}
    failed = outcome.failed.set_index("_source_row")["reject_reasons"].to_dict()
    assert 3 in failed and "exceeds max length 50" in failed[3]


def test_schema_checks_type_length_and_range():
    schema = {
        "dmu_hospitalised_tba_missing": {"kind": "str", "length": 50, "nullable": True},
        "age": {"kind": "int", "length": None, "nullable": True, "min": -32768, "max": 32767},
        "date_of_onset_symptoms": {"kind": "date", "length": None, "nullable": True},
    }
    df = pd.DataFrame(
        {
            "_source_row": [2, 3, 4, 5],
            "dmu_hospitalised_tba_missing": ["ok", "Y" * 60, "ok", "ok"],
            "age": [30, 40, "not-a-number", 50],
            "date_of_onset_symptoms": [
                dt.date(2024, 1, 1), dt.date(2024, 1, 1), dt.date(2024, 1, 1), "2024-13-40",
            ],
        }
    )
    outcome = validate_dataframe(df, {"conditional_rules": True}, schema=schema)
    failed = outcome.failed.set_index("_source_row")["reject_reasons"].to_dict()
    cols = outcome.failed.set_index("_source_row")["failed_columns"].to_dict()
    assert set(outcome.passed["_source_row"]) == {2}
    # reason names the column and the rule/expectation; failed_columns lists the column
    assert "dmu_hospitalised_tba_missing: exceeds max length 50" in failed[3]
    assert "dmu_hospitalised_tba_missing" in cols[3]
    assert "age: is not an integer" in failed[4] and "age" in cols[4]
    assert "date_of_onset_symptoms: is not a valid date" in failed[5]
    assert "date_of_onset_symptoms" in cols[5]


def test_validate_splits_pass_fail():
    outcome = validate_dataframe(_df(), CFG)
    failed_rows = set(outcome.failed["_source_row"])
    # rows 3 (age), 4 (gender), 5 (date order) should fail; row 2 passes.
    assert 2 in set(outcome.passed["_source_row"])
    assert {3, 4, 5} <= failed_rows
    assert outcome.n_passed + outcome.n_failed == 4
    assert "reject_reasons" in outcome.failed.columns
    assert outcome.failed.loc[outcome.failed["_source_row"] == 3, "reject_reasons"].iloc[0]
