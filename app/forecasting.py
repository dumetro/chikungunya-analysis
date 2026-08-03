"""Case-progression forecasting and rolling-window surveillance helpers.

Pure pandas/numpy (no scipy) so the functions run anywhere the dashboard runs
and stay unit-testable. Two capabilities:

* :func:`forecast_weekly` — projects weekly notified cases forward by fitting a
  log-linear decay to the observed post-peak decline, modulated by a Southern-
  Hemisphere (austral) transmission-seasonality index, with an 80% band and a
  slower-decaying "resurgence" contingency line.
* :func:`rolling_windows` — 24-hour / 3-day / 7-day case counts anchored at the
  latest reported day, each compared with the immediately preceding period, plus
  a daily series with a 7-day moving average and the most active localities.

Both operate on the cleaned case frame from :mod:`data_access` and respect
whatever subset (filters) is passed in. See
``docs/forecast_methodology.md`` for the model rationale.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

# Relative monthly transmission suitability for Aedes-borne spread in Mauritius
# (Southern Hemisphere): summer (Nov–Apr) favourable, austral winter (Jun–Aug)
# suppressed, October warming as the season turns. Used as a multiplicative
# modifier on the fitted decay, normalised to the last observed month.
MONTHLY_SUITABILITY = {
    1: 1.30, 2: 1.30, 3: 1.25, 4: 1.10, 5: 0.95, 6: 0.82,
    7: 0.80, 8: 0.80, 9: 0.92, 10: 1.10, 11: 1.20, 12: 1.28,
}

DEFAULT_DATE_COL = "date_of_notification"
DATE_COL_FALLBACKS = [
    "date_of_notification", "date_of_onset_symptoms", "date_of_sample_taken",
]


def pick_date_col(df: pd.DataFrame, preferred: str | None = None) -> str | None:
    """Return the first usable (present and non-empty) date column."""
    order = ([preferred] if preferred else []) + DATE_COL_FALLBACKS
    for c in order:
        if c and c in df.columns and df[c].notna().any():
            return c
    return None


def weekly_counts(df: pd.DataFrame, date_col: str = DEFAULT_DATE_COL) -> pd.DataFrame:
    """Weekly case counts (week starting Monday), zero-filled across the range."""
    empty = pd.DataFrame(columns=["week_start", "cases"])
    if date_col not in df.columns:
        return empty
    s = df[[date_col]].dropna()
    if s.empty:
        return empty
    wk = s[date_col].dt.to_period("W").dt.start_time
    counts = wk.value_counts().sort_index()
    full = pd.date_range(counts.index.min(), counts.index.max(), freq="W-MON")
    counts = counts.reindex(full, fill_value=0)
    return pd.DataFrame({"week_start": counts.index, "cases": counts.to_numpy(dtype=int)})


def daily_counts(df: pd.DataFrame, date_col: str = DEFAULT_DATE_COL,
                 days: int = 28) -> pd.DataFrame:
    """Daily counts for the last ``days`` (zero-filled) with a 7-day moving average."""
    empty = pd.DataFrame(columns=["day", "cases", "ma7"])
    if date_col not in df.columns:
        return empty
    s = df[[date_col]].dropna()
    if s.empty:
        return empty
    d = s[date_col].dt.normalize()
    anchor = d.max()
    # Pull an extra 6 days so the moving average is defined on the first shown day.
    start = anchor - pd.Timedelta(days=days - 1 + 6)
    idx = pd.date_range(start, anchor, freq="D")
    counts = d.value_counts().reindex(idx, fill_value=0)
    ma = counts.rolling(7, min_periods=1).mean()
    out = pd.DataFrame({"day": idx, "cases": counts.to_numpy(dtype=int),
                        "ma7": ma.to_numpy().round(1)})
    return out.tail(days).reset_index(drop=True)


@dataclass
class ForecastResult:
    """Container for :func:`forecast_weekly` output."""

    observed: pd.DataFrame                       # week_start, cases
    forecast: pd.DataFrame                       # week_start, cases, lo, hi, resurgence
    monthly: pd.DataFrame                        # month, cases, lo, hi
    meta: dict = field(default_factory=dict)     # decay_k, half_life_wk, peak, anchor_month …


def _trim_incomplete_week(obs: pd.DataFrame, max_day: pd.Timestamp) -> pd.DataFrame:
    """Drop the final week if the data ends before that week is complete.

    Partial weeks read as an artificial collapse (right-truncation) and would
    corrupt any trend fit, so they are excluded from both the fit and the plotted
    history.
    """
    if obs.empty:
        return obs
    last_start = obs["week_start"].iloc[-1]
    if max_day < last_start + pd.Timedelta(days=6):
        return obs.iloc[:-1].reset_index(drop=True)
    return obs


def _fit_decay(cases: np.ndarray) -> tuple[float, float, int, str]:
    """Fit ``y = a * exp(-k*t)`` on the post-peak decline (log-linear least squares).

    Returns ``(a, k, t_last, mode)`` where ``t_last`` is the time index of the
    last observed point on the fitted segment. When the series has not yet
    established a post-peak decline (peak within the last two points), falls back
    to a flat "level" model (``k = 0``) anchored on the recent mean, so the
    projection never invents a decline — or a spurious one — that the data
    doesn't support.
    """
    peak_idx = int(np.argmax(cases))
    tail = cases[peak_idx:]
    if len(tail) >= 3:
        t = np.arange(len(tail), dtype=float)
        y = np.log(np.maximum(tail.astype(float), 1.0))
        A = np.vstack([np.ones_like(t), t]).T
        intercept, slope = np.linalg.lstsq(A, y, rcond=None)[0]
        a = float(np.exp(intercept))
        k = float(max(-slope, 0.0))
        return a, k, len(tail) - 1, "decay"
    # No established decline yet — hold the recent level, let seasonality modulate.
    recent = cases[-min(3, len(cases)):]
    return float(np.mean(recent)), 0.0, 0, "level"


def forecast_weekly(df: pd.DataFrame, date_col: str = DEFAULT_DATE_COL,
                    horizon_weeks: int = 13, dispersion: float = 0.35,
                    z: float = 1.28) -> ForecastResult | None:
    """Project weekly cases ``horizon_weeks`` ahead. ``None`` if too little data.

    The point forecast is the fitted exponential decay times a seasonal factor
    (``MONTHLY_SUITABILITY`` normalised to the last observed month). The 80% band
    (``z=1.28``) widens with horizon. The resurgence line decays more slowly and
    responds more strongly to seasonal warming, flagging spring re-emergence risk.
    """
    obs_full = weekly_counts(df, date_col)
    if len(obs_full) < 4:
        return None
    max_day = df[date_col].dropna().max().normalize()
    obs = _trim_incomplete_week(obs_full, max_day)
    if len(obs) < 4:
        return None

    cases = obs["cases"].to_numpy()
    a, k, t_last, mode = _fit_decay(cases)
    peak_idx = int(np.argmax(cases))
    anchor_month = obs["week_start"].iloc[-1].month
    anchor_suit = MONTHLY_SUITABILITY.get(anchor_month, 1.0)
    floor = max(1.0, round(0.01 * cases.max()))

    rows = []
    last_week = obs["week_start"].iloc[-1]
    for i in range(1, horizon_weeks + 1):
        ws = last_week + pd.Timedelta(weeks=i)
        m = ws.month
        seas = MONTHLY_SUITABILITY.get(m, 1.0) / anchor_suit
        base = a * np.exp(-k * (t_last + i))
        mu = max(base * seas, floor)
        sigma = mu * dispersion * np.sqrt(1 + 0.12 * (i - 1))
        lo = max(0.0, mu - z * sigma)
        hi = mu + z * sigma
        base_r = a * np.exp(-0.55 * k * (t_last + i))
        seas_r = (MONTHLY_SUITABILITY.get(m, 1.0) / anchor_suit) ** 1.6
        resurg = max(base_r * seas_r, mu)
        rows.append({"week_start": ws, "cases": int(round(mu)),
                     "lo": int(round(lo)), "hi": int(round(hi)),
                     "resurgence": int(round(resurg))})
    fc = pd.DataFrame(rows)

    fc_m = fc.assign(month=fc["week_start"].dt.to_period("M"))
    monthly = (fc_m.groupby("month")[["cases", "lo", "hi"]].sum()
               .reset_index())
    monthly["month"] = monthly["month"].dt.strftime("%b %Y")

    half_life = (np.log(2) / k) if k > 0 else float("inf")
    meta = {
        "mode": mode,
        "decay_k": round(k, 3),
        "half_life_wk": round(half_life, 1) if np.isfinite(half_life) else None,
        "peak_week": obs["week_start"].iloc[peak_idx].date().isoformat(),
        "peak_cases": int(cases.max()),
        "anchor_month": anchor_month,
        "current_rate_wk": int(cases[-1]),
        "trimmed_partial_week": len(obs) < len(obs_full),
        "horizon_weeks": horizon_weeks,
        "horizon_total": int(fc["cases"].sum()),
        "horizon_lo": int(fc["lo"].sum()),
        "horizon_hi": int(fc["hi"].sum()),
    }
    return ForecastResult(observed=obs, forecast=fc, monthly=monthly, meta=meta)


def _pct(cur: int, prev: int) -> float | None:
    if not prev:
        return None
    return round((cur - prev) / prev * 100, 0)


def rolling_windows(df: pd.DataFrame, date_col: str = DEFAULT_DATE_COL,
                    anchor: pd.Timestamp | None = None,
                    area_col: str = "locality") -> dict | None:
    """24h / 3d / 7d case counts vs the preceding period, anchored at the latest day.

    Returns a dict with per-window counts/deltas, the anchor date, a daily series
    (with 7-day moving average) and the most active areas over the 7-day window.
    ``None`` if there are no dated cases.
    """
    if date_col not in df.columns:
        return None
    s = df.dropna(subset=[date_col])
    if s.empty:
        return None
    day = s[date_col].dt.normalize()
    if anchor is None:
        anchor = day.max()
    anchor = pd.Timestamp(anchor).normalize()

    def between(lo_excl: pd.Timestamp, hi_incl: pd.Timestamp) -> int:
        return int(((day > lo_excl) & (day <= hi_incl)).sum())

    windows = []
    for label, n in [("24 hours", 1), ("3 days", 3), ("7 days", 7)]:
        cur_lo = anchor - pd.Timedelta(days=n)
        cur = between(cur_lo, anchor)
        prev = between(cur_lo - pd.Timedelta(days=n), cur_lo)
        windows.append({
            "label": label, "days": n, "count": cur,
            "per_day": round(cur / n, 0), "prev": prev,
            "delta_pct": _pct(cur, prev),
            "provisional": n == 1,     # a single day is always incomplete
        })

    # Most active areas over the trailing 7 days.
    top_areas = []
    if area_col in s.columns:
        wk = s[(day > anchor - pd.Timedelta(days=7)) & (day <= anchor)]
        vc = wk[area_col].dropna().value_counts().head(5)
        top_areas = [{"area": a, "count": int(c)} for a, c in vc.items()]

    return {
        "anchor": anchor,
        "windows": windows,
        "daily": daily_counts(df, date_col, days=28),
        "top_areas": top_areas,
        "date_col": date_col,
    }
