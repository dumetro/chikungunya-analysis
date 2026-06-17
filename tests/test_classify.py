"""Unit tests for case classification driven by config/case_definitions.yaml."""

import pandas as pd

from chikungunya_pipeline.classify import classify_case, classify_cases, load_case_definitions


def test_definitions_load():
    d = load_case_definitions()
    assert d["meta"]["default_scheme"] == "who_paho"
    assert "who_paho" in d["schemes"] and "cdc" in d["schemes"]


def test_classify_priority_rules():
    df = pd.DataFrame(
        {
            "pcr_result": ["Positive", "Negative", "Negative", "Not Done"],
            "epi_linkage": ["", "Case-12", "", None],
            "symptoms": [
                "Fever; Arthralgia",       # PCR+ -> Confirmed (PCR wins)
                "Fever; Joint pain",       # clinical + epi link -> Probable
                "Fever; Arthralgia",       # clinical only -> Suspected
                "Headache",                # no clinical, no PCR -> Unclassified
            ],
        }
    )
    result = classify_cases(df).tolist()
    assert result == ["Confirmed", "Probable", "Suspected", "Unclassified"]


def test_unclassified_reasons():
    from chikungunya_pipeline.classify import classify_cases_with_reasons
    df = pd.DataFrame(
        {
            "pcr_result": ["Negative", "Negative", "Positive"],
            "epi_linkage": ["", "", ""],
            "symptoms": ["Headache", "Fever", "Fever; Arthralgia"],
        }
    )
    labels, reasons = classify_cases_with_reasons(df)
    assert labels.tolist() == ["Unclassified", "Unclassified", "Confirmed"]
    # row 0: not pcr-positive + missing both fever & arthralgia
    assert "not PCR-positive" in reasons.iloc[0]
    assert "fever" in reasons.iloc[0] and "arthralgia" in reasons.iloc[0]
    # row 1: has fever, missing arthralgia only
    assert "arthralgia" in reasons.iloc[1] and "fever" not in reasons.iloc[1].split("missing")[1]
    # classified rows have no reason
    assert reasons.iloc[2] == ""


def test_fit_age_groups_overwrites_from_age():
    from chikungunya_pipeline.classify import fit_age_groups
    allowed = ["0-19", "20-39", "40-59", "60-150"]
    df = pd.DataFrame(
        {
            "_sn": ["1", "2", "3", "4", "5"],
            "_source_row": [2, 3, 4, 5, 6],
            "age": [34, 70, 10, 55, None],
            "age_group": ["20-39", "60 and above", None, "40-59", "30-40"],
        }
    )
    out, records = fit_age_groups(df, allowed)
    groups = out.set_index("_sn")["age_group"].to_dict()
    assert groups["1"] == "20-39"      # already canonical -> untouched
    assert groups["2"] == "60-150"     # "60 and above" -> derived from age 70
    assert groups["3"] == "0-19"       # missing -> derived from age 10
    assert groups["4"] == "40-59"      # already canonical -> untouched
    assert groups["5"] == "30-40"      # non-canonical but age is None -> left as-is
    fixed = {r["sn"] for r in records}
    assert fixed == {"2", "3"}
    assert all(r["action"] == "age_group_from_age" for r in records)


def test_classify_single_record():
    rec = {"pcr_result": "Positive", "epi_linkage": None, "symptoms": "Fever"}
    assert classify_case(rec) == "Confirmed"
    rec2 = {"pcr_result": "Negative", "epi_linkage": None, "symptoms": "Fever; Arthritis"}
    assert classify_case(rec2) == "Suspected"
