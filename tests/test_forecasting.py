"""Unit tests for the case-forecasting and rolling-window helpers (app/forecasting.py)."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# forecasting.py lives in app/, which isn't on the default (src) pythonpath.
_APP = Path(__file__).resolve().parents[1] / "app"
if str(_APP) not in sys.path:
    sys.path.insert(0, str(_APP))

import forecasting as F  # noqa: E402


def _series(weekly: dict[int, int], start="2026-01-05", seed=0) -> pd.DataFrame:
    """Build a line-list DataFrame from {epi_week: count} by notification date."""
    rng = np.random.default_rng(seed)
    mon = pd.Timestamp(start)
    rows = []
    for wk, n in weekly.items():
        ws = mon + pd.Timedelta(weeks=wk - 2)
        rows += [ws + pd.Timedelta(days=int(rng.integers(0, 7))) for _ in range(n)]
    return pd.DataFrame({"date_of_notification": pd.to_datetime(rows)})


def test_weekly_counts_zero_filled_and_ordered():
    df = _series({10: 5, 12: 7})  # gap at week 11
    wk = F.weekly_counts(df)
    assert list(wk["cases"]) == [5, 0, 7]
    assert wk["week_start"].is_monotonic_increasing


def test_forecast_decay_on_rise_and_fall():
    df = _series({10: 40, 11: 80, 12: 160, 13: 320, 14: 560, 15: 700,
                  16: 600, 17: 460, 18: 340, 19: 250, 20: 180, 21: 130, 22: 90})
    res = F.forecast_weekly(df, horizon_weeks=12)
    assert res is not None
    assert res.meta["mode"] == "decay"
    assert res.meta["decay_k"] > 0            # a real decline was detected
    # Band ordering and resurgence dominance hold for every forecast week.
    assert (res.forecast["hi"] >= res.forecast["cases"]).all()
    assert (res.forecast["cases"] >= res.forecast["lo"]).all()
    assert (res.forecast["resurgence"] >= res.forecast["cases"]).all()
    assert len(res.forecast) == 12


def test_forecast_level_when_not_yet_peaked():
    df = _series({10: 50, 11: 90, 12: 150, 13: 250, 14: 400, 15: 550})  # still rising
    res = F.forecast_weekly(df, horizon_weeks=8)
    assert res is not None
    assert res.meta["mode"] == "level"        # no post-peak decline to fit
    assert res.meta["decay_k"] == 0.0


def test_forecast_needs_minimum_history():
    df = _series({10: 5, 11: 6, 12: 7})       # only 3 weeks
    assert F.forecast_weekly(df) is None


def test_trims_incomplete_final_week():
    # Enough weeks that trimming still leaves >= 4; data ends mid-week so the
    # final partial week must be excluded from the fit.
    df = _series({10: 60, 11: 90, 12: 120, 13: 150, 14: 180, 15: 200, 16: 220})
    df = df[df["date_of_notification"] <= "2026-04-15"]  # Wednesday inside week 16
    res = F.forecast_weekly(df, horizon_weeks=6)
    assert res is not None
    assert res.meta["trimmed_partial_week"] is True
    # The excluded week must not appear in the observed (fitted) history.
    assert res.observed["week_start"].max() < pd.Timestamp("2026-04-13")


def test_rolling_windows_counts_and_deltas():
    anchor = pd.Timestamp("2026-05-20")
    days = ([anchor] * 10                                   # 24h window: 10
            + [anchor - pd.Timedelta(days=1)] * 5           # into 3d/7d
            + [anchor - pd.Timedelta(days=2)] * 5
            + [anchor - pd.Timedelta(days=8)] * 4)          # prior 7d window
    df = pd.DataFrame({"date_of_notification": pd.to_datetime(days)})
    rw = F.rolling_windows(df)
    w = {x["label"]: x for x in rw["windows"]}
    assert rw["anchor"] == anchor
    assert w["24 hours"]["count"] == 10
    assert w["3 days"]["count"] == 20          # 10 + 5 + 5
    assert w["7 days"]["count"] == 20          # nothing between day 3 and 7
    assert w["7 days"]["prev"] == 4            # the day-8 cases
    assert w["24 hours"]["provisional"] is True


def test_rolling_windows_empty():
    df = pd.DataFrame({"date_of_notification": pd.to_datetime([])})
    assert F.rolling_windows(df) is None
