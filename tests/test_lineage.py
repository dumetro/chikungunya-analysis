"""Unit tests for data-lineage corrections and normalization diffing."""

import pandas as pd

from chikungunya_pipeline.lineage import apply_corrections, diff_records


def test_move_correction_relocates_and_logs():
    df = pd.DataFrame(
        {
            "_sn": ["1001", "1002"],
            "_source_row": [2, 3],
            "pregnancy": ["Fever, joint pain", "Yes"],   # SN 1001: symptom in pregnancy col
            "symptoms": [None, "Rash"],
        }
    )
    corrections = {"1001": [{"action": "move", "from": "pregnancy", "to": "symptoms"}]}
    out, records = apply_corrections(df, corrections)

    row = out[out["_sn"] == "1001"].iloc[0]
    assert row["pregnancy"] is None                      # source cleared
    assert row["symptoms"] == "Fever, joint pain"        # moved into target
    # untouched row unchanged
    assert out[out["_sn"] == "1002"].iloc[0]["pregnancy"] == "Yes"
    # two events logged (move_in + move_out), naming the columns
    actions = {(r["column_name"], r["action"]) for r in records}
    assert ("symptoms", "move_in<-pregnancy") in actions
    assert ("pregnancy", "move_out->symptoms") in actions
    assert all(r["sn"] == "1001" for r in records)


def test_clear_and_set_corrections():
    df = pd.DataFrame({"_sn": ["7"], "_source_row": [2],
                       "gestation_week": ["20"], "gender": ["m"]})
    corrections = {"7": [{"action": "clear", "column": "gestation_week"},
                         {"action": "set", "column": "gender", "value": "Female"}]}
    out, records = apply_corrections(df, corrections)
    assert out.iloc[0]["gestation_week"] is None
    assert out.iloc[0]["gender"] == "Female"
    assert {r["action"] for r in records} == {"clear", "set"}


def test_diff_records_logs_only_changed_cells():
    before = pd.DataFrame({"_sn": ["1", "2"], "_source_row": [2, 3],
                           "occupation": ["teacher", "nurse"]})
    after = before.copy()
    after.loc[0, "occupation"] = "Teacher"   # normalized; row 2 unchanged
    recs = diff_records(before, after, stage="normalize", action="normalize",
                        columns=["occupation"])
    assert len(recs) == 1
    assert recs[0]["sn"] == "1"
    assert recs[0]["old_value"] == "teacher" and recs[0]["new_value"] == "Teacher"


def test_no_corrections_is_noop():
    df = pd.DataFrame({"_sn": ["1"], "_source_row": [2], "pregnancy": ["Yes"]})
    out, records = apply_corrections(df, {})
    assert records == []
    assert out.equals(df)
