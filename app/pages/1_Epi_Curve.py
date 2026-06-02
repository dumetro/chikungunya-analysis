"""Epidemic curve: onset/notification timelines and cumulative incidence."""

from __future__ import annotations

import plotly.express as px
import streamlit as st

from data_access import apply_filters, load_cases
from filters import sidebar_filters
from theme import who_style as who

st.set_page_config(page_title="Epi Curve", page_icon="📈", layout="wide")
who.apply_theme()
who.header("Epidemic Curve", "Case counts over time by onset and notification date")

df = load_cases()
fdf = apply_filters(df, sidebar_filters(df))

freq_label = st.radio("Time resolution", ["Weekly", "Daily"], horizontal=True)
rule = "W" if freq_label == "Weekly" else "D"

col = st.selectbox(
    "Date basis",
    [c for c in ["date_of_onset_symptoms", "date_of_notification", "date_of_sample_taken"] if c in fdf],
    format_func=lambda c: c.replace("_", " ").title(),
)

series = fdf.dropna(subset=[col])
if series.empty:
    st.info("No dated cases for the current filter.")
    st.stop()

curve = (
    series.assign(bucket=lambda d: d[col].dt.to_period(rule).dt.start_time)
    .groupby("bucket")
    .size()
    .reset_index(name="cases")
    .sort_values("bucket")
)
curve["cumulative"] = curve["cases"].cumsum()

fig = px.bar(curve, x="bucket", y="cases", labels={"bucket": "Date", "cases": "Cases"},
             title=f"Cases by {freq_label.lower()} {col.replace('_', ' ')}")
fig.update_traces(marker_color=who.WHO_BLUE)
st.plotly_chart(who.style_fig(fig), use_container_width=True)

fig2 = px.area(curve, x="bucket", y="cumulative", labels={"bucket": "Date", "cumulative": "Cumulative cases"},
               title="Cumulative incidence")
fig2.update_traces(line_color=who.WHO_DARK, fillcolor="rgba(0,147,213,0.2)")
st.plotly_chart(who.style_fig(fig2), use_container_width=True)
