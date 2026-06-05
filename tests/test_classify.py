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


def test_classify_single_record():
    rec = {"pcr_result": "Positive", "epi_linkage": None, "symptoms": "Fever"}
    assert classify_case(rec) == "Confirmed"
    rec2 = {"pcr_result": "Negative", "epi_linkage": None, "symptoms": "Fever; Arthritis"}
    assert classify_case(rec2) == "Suspected"
