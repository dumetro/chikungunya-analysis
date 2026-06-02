"""Unit tests for the dedicated ISO-8601 date normaliser."""

import datetime as dt

import pandas as pd
import pytest

from chikungunya_pipeline.dates import to_iso8601, to_iso_string


@pytest.mark.parametrize("value", ["", "  ", "NA", "n/a", "-", "unknown", None, float("nan")])
def test_blanks_become_none(value):
    assert to_iso8601(value) is None


def test_iso_string():
    assert to_iso8601("2024-01-15") == dt.date(2024, 1, 15)


def test_day_first_ambiguous():
    # 03/04/2024 -> 3 April (day-first default)
    assert to_iso8601("03/04/2024") == dt.date(2024, 4, 3)
    # month-first override
    assert to_iso8601("03/04/2024", dayfirst=False) == dt.date(2024, 3, 4)


def test_unambiguous_day_first():
    assert to_iso8601("25/12/2023") == dt.date(2023, 12, 25)


def test_dash_and_dot_separators():
    assert to_iso8601("25-12-2023") == dt.date(2023, 12, 25)
    assert to_iso8601("25.12.2023") == dt.date(2023, 12, 25)


def test_textual_months():
    assert to_iso8601("12 Jan 2024") == dt.date(2024, 1, 12)
    assert to_iso8601("Jan 12, 2024") == dt.date(2024, 1, 12)


def test_excel_serial_number():
    # 45292 == 2024-01-01 in the 1900 date system.
    assert to_iso8601(45292) == dt.date(2024, 1, 1)
    assert to_iso8601("45292") == dt.date(2024, 1, 1)
    assert to_iso8601(45292.0) == dt.date(2024, 1, 1)


def test_passthrough_date_types():
    assert to_iso8601(dt.date(2024, 5, 1)) == dt.date(2024, 5, 1)
    assert to_iso8601(dt.datetime(2024, 5, 1, 13, 0)) == dt.date(2024, 5, 1)
    assert to_iso8601(pd.Timestamp("2024-05-01")) == dt.date(2024, 5, 1)
    assert to_iso8601(pd.NaT) is None


def test_garbage_returns_none():
    assert to_iso8601("not a date") is None
    assert to_iso8601("32/13/2024") is None


def test_small_number_not_treated_as_serial():
    # An age-like value should not parse as a date.
    assert to_iso8601(42) is None


def test_iso_string_helper():
    assert to_iso_string("03/04/2024") == "2024-04-03"
    assert to_iso_string("") is None
