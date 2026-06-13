"""Unit tests for the sanitisation helpers."""

import datetime as dt

import pandas as pd

from chikungunya_pipeline.mapping_config import load_mapping
from chikungunya_pipeline.sanitize import (
    clean_gender,
    clean_int,
    clean_string,
    clean_yes_no,
    sanitize_dataframe,
)


def test_clean_string():
    assert clean_string("  hello   world ") == "hello world"
    assert clean_string("NA") is None
    assert clean_string("") is None
    assert clean_string(None) is None
    assert clean_string(float("nan")) is None


def test_clean_yes_no():
    assert clean_yes_no("Y") == "Yes"
    assert clean_yes_no("yes") == "Yes"
    assert clean_yes_no("No") == "No"
    assert clean_yes_no("maybe") is None


def test_clean_gender():
    assert clean_gender("M") == "Male"
    assert clean_gender("female") == "Female"
    assert clean_gender("other") is None


def test_clean_int_range():
    assert clean_int("42") == 42
    assert clean_int("42.0") == 42
    assert clean_int("200", lo=0, hi=120) is None
    assert clean_int("-1", lo=0, hi=120) is None
    assert clean_int("abc") is None


def test_sanitize_dataframe_clears_gestation_when_not_pregnant():
    mapping = load_mapping()
    df = pd.DataFrame(
        {
            "_source_row": [2, 3],
            "pregnancy": ["No", "Yes"],
            "gestation_week": ["20", "30"],
            "gender": ["m", "F"],
            "date_of_onset_symptoms": ["03/04/2026", ""],
        }
    )
    out = sanitize_dataframe(df, mapping)
    assert out.loc[0, "gestation_week"] is None  # not pregnant -> cleared
    assert out.loc[1, "gestation_week"] == 30
    assert out.loc[0, "gender"] == "Male"
    assert out.loc[1, "gender"] == "Female"
    # 2026 regardless of whether DATA_YEAR forcing is enabled
    assert out.loc[0, "date_of_onset_symptoms"] == dt.date(2026, 4, 3)
    assert out.loc[1, "date_of_onset_symptoms"] is None
