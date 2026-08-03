"""Shared Streamlit UI blocks for surveillance analytics.

Rendering that is reused across pages lives here so the overview and
surveillance views stay visually and numerically consistent:

* :func:`rolling_case_panel` — 24h / 3d / 7d case tiles (with period-over-period
  deltas) and, optionally, a daily epidemic curve with a 7-day moving average.
* :func:`case_forecast_section` — observed weekly cases plus the projected
  trajectory, 80% band and resurgence-risk line, with a monthly summary.

Compute lives in :mod:`forecasting` (pure, tested); this module only draws.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import forecasting as fc
from theme import who_style as who


def rolling_case_panel(df: pd.DataFrame, date_col: str | None = None,
                       show_chart: bool = True, days: int = 28,
                       key: str = "roll") -> None:
    """Render the 24h / 3d / 7d rolling-window case panel.

    ``show_chart=False`` renders just the metric tiles (for the overview page);
    ``True`` adds the daily curve + 7-day moving average and a top-areas caption.
    """
    col = fc.pick_date_col(df, date_col)
    if col is None:
        st.info("No usable case dates for the current filter.")
        return
    rw = fc.rolling_windows(df, col)
    if rw is None:
        st.info("No dated cases for the current filter.")
        return

    tiles = st.columns(3)
    for tile, w in zip(tiles, rw["windows"]):
        delta = None if w["delta_pct"] is None else f"{w['delta_pct']:+.0f}% vs prev {w['label']}"
        help_txt = (f"{w['count']:,} in the last {w['label']} "
                    f"({w['per_day']:.0f}/day); previous {w['label']}: {w['prev']:,}."
                    + (" Most recent day is provisional (reporting lag)." if w["provisional"] else ""))
        label = f"Last {w['label']}" + (" ⚠️" if w["provisional"] else "")
        # Rising case counts are a concern → inverse colouring (up = red).
        tile.metric(label, f"{w['count']:,}", delta=delta,
                    delta_color="inverse" if delta else "off", help=help_txt)

    anchor = pd.Timestamp(rw["anchor"]).date()
    basis = col.replace("_", " ")
    st.caption(
        f"Anchored at {anchor} ({basis}). Shorter windows are dominated by "
        "reporting rhythm — read them against the 7-day figure, and treat the "
        "most recent day as provisional.")

    if not show_chart:
        return

    daily = rw["daily"]
    if not daily.empty:
        fig = go.Figure()
        fig.add_bar(x=daily["day"], y=daily["cases"], name="Daily cases",
                    marker_color=who.WHO_BLUE)
        fig.add_scatter(x=daily["day"], y=daily["ma7"], name="7-day average",
                        mode="lines", line=dict(color=who.WHO_AMBER, width=2.5))
        fig.update_layout(
            title=f"Daily cases (last {days} days) with 7-day moving average",
            xaxis_title="Day", yaxis_title="Cases",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        )
        st.plotly_chart(who.style_fig(fig, height=340), use_container_width=True,
                        key=f"{key}_daily")

    if rw["top_areas"]:
        top = ", ".join(f"{a['area']} ({a['count']})" for a in rw["top_areas"][:5])
        st.caption(f"Most active areas over the last 7 days: {top}.")

    who.notes(
        "Rolling case counts for the last 24 hours, 3 days and 7 days, each "
        "compared with the immediately preceding period, plus the daily epidemic "
        "curve and its 7-day moving average. The moving average — not any single "
        "day — carries the trend.",
        "Requires a populated case date (defaults to notification date). The most "
        "recent day and the shorter windows are sensitive to reporting lag "
        "(right-truncation) and weekend effects, so a fall there can be an "
        "artefact rather than a real decline; the 7-day view is the reliable "
        "signal. Needs a daily-updated line list to be meaningful in real time.")


def case_forecast_section(df: pd.DataFrame, date_col: str | None = None,
                          horizon_weeks: int = 13, key: str = "fc") -> None:
    """Render the case-progression forecast: observed + projection + band."""
    col = fc.pick_date_col(df, date_col)
    if col is None:
        st.info("No usable case dates to build a forecast.")
        return
    res = fc.forecast_weekly(df, col, horizon_weeks=horizon_weeks)
    if res is None:
        st.info("Not enough weekly history (need ≥4 weeks) to build a forecast.")
        return

    obs, f, meta = res.observed, res.forecast, res.meta

    # Connect the last observed point to the forecast so the lines join cleanly.
    bridge = pd.DataFrame([{
        "week_start": obs["week_start"].iloc[-1], "cases": int(obs["cases"].iloc[-1]),
        "lo": int(obs["cases"].iloc[-1]), "hi": int(obs["cases"].iloc[-1]),
        "resurgence": int(obs["cases"].iloc[-1]),
    }])
    fb = pd.concat([bridge, f], ignore_index=True)

    fig = go.Figure()
    # 80% band (upper then lower with fill).
    fig.add_scatter(x=fb["week_start"], y=fb["hi"], mode="lines",
                    line=dict(width=0), hoverinfo="skip", showlegend=False)
    fig.add_scatter(x=fb["week_start"], y=fb["lo"], mode="lines", line=dict(width=0),
                    fill="tonexty", fillcolor="rgba(0,147,213,0.15)",
                    name="80% interval", hoverinfo="skip")
    # Observed weekly cases.
    fig.add_bar(x=obs["week_start"], y=obs["cases"], name="Observed",
                marker_color=who.WHO_BLUE)
    # Point forecast.
    fig.add_scatter(x=fb["week_start"], y=fb["cases"], mode="lines",
                    name="Forecast", line=dict(color=who.WHO_DARK, width=2.5, dash="dot"))
    # Resurgence contingency.
    fig.add_scatter(x=fb["week_start"], y=fb["resurgence"], mode="lines",
                    name="Resurgence scenario",
                    line=dict(color=who.WHO_RED, width=1.8, dash="dash"))
    fig.update_layout(
        title=f"Weekly cases: observed and {horizon_weeks}-week forecast",
        xaxis_title="Week", yaxis_title="Cases",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    st.plotly_chart(who.style_fig(fig, height=440), use_container_width=True,
                    key=f"{key}_chart")

    # Monthly summary tiles for the next few whole months.
    if not res.monthly.empty:
        cols = st.columns(min(len(res.monthly), 4))
        for c, (_, r) in zip(cols, res.monthly.head(4).iterrows()):
            c.metric(r["month"], f"{int(r['cases']):,}",
                     help=f"80% interval {int(r['lo']):,}–{int(r['hi']):,}")

    hl = (f"a case half-life of ~{meta['half_life_wk']} weeks"
          if meta.get("mode") == "decay" and meta.get("half_life_wk")
          else "no established post-peak decline yet, so the recent level is held")
    trimmed = " The final partial reporting week is excluded from the fit." if meta.get("trimmed_partial_week") else ""
    st.caption(
        f"Peak of {meta['peak_cases']:,}/week around {meta['peak_week']}; latest "
        f"complete week {meta['current_rate_wk']:,}. Projection implies {hl}. "
        f"Next {horizon_weeks} weeks: {meta['horizon_total']:,} cases "
        f"(80% interval {meta['horizon_lo']:,}–{meta['horizon_hi']:,}).{trimmed}")

    who.notes(
        "Projected weekly case progression. The point forecast fits a log-linear "
        "decay to the observed post-peak decline and modulates it by Southern-"
        "Hemisphere transmission seasonality (austral winter suppresses spread; "
        "October warming lifts it). The shaded band is an 80% interval that widens "
        "with horizon; the dashed red line is a resurgence contingency (slower "
        "decay + stronger seasonal response) flagging spring re-emergence risk.",
        "This is a statistical extrapolation, not a mechanistic transmission "
        "model: it does not represent susceptibles, importation shocks, "
        "vaccination or intervention intensity, and it assumes reporting stays "
        "consistent. When the series has not yet peaked it holds the recent level "
        "and relies on seasonality — treat those projections as indicative. "
        "Re-fits automatically as new weeks load; revise expectations as each "
        "Sitrep arrives.")
