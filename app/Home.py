"""Chikungunya Outbreak Surveillance Dashboard — overview / landing page.

Run with:  streamlit run app/Home.py
"""

from __future__ import annotations

from datetime import date

import plotly.express as px
import streamlit as st

from data_access import apply_filters, kpi_summary, load_cases
from filters import sidebar_filters
from theme import who_style as who

st.set_page_config(page_title="Chikungunya Surveillance", page_icon="🦟", layout="wide")
who.apply_theme()

who.header(
    "Chikungunya Outbreak Surveillance",
    f"Case-level analysis dashboard · data as of {date.today().isoformat()}",
)

try:
    df = load_cases()
except Exception as exc:
    st.error(
        "Could not load data from the database. Check `DATABASE_URL` in your `.env` "
        f"and that the pipeline has loaded data.\n\n```\n{exc}\n```"
    )
    st.stop()

if df.empty:
    st.warning("No cases found in `chikungunya_analysis`. Run the pipeline to load data.")
    st.stop()

filters = sidebar_filters(df)
fdf = apply_filters(df, filters)

# --- Headline KPIs ---------------------------------------------------------
k = kpi_summary(fdf)
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total cases", f"{k['total_cases']:,}")
c2.metric("PCR positive", f"{k['pcr_positive']:,}")
c3.metric("PCR positivity", f"{k['pcr_positivity_pct']}%")
c4.metric("Admitted", f"{k['admitted']:,}")
c5.metric("Case fatality", f"{k['cfr_pct']}%")

st.divider()

# --- Epi curve preview -----------------------------------------------------
left, right = st.columns([2, 1])
with left:
    st.subheader("Epidemic curve (by onset week)")
    if "date_of_onset_symptoms" in fdf and fdf["date_of_onset_symptoms"].notna().any():
        weekly = (
            fdf.dropna(subset=["date_of_onset_symptoms"])
            .assign(week=lambda d: d["date_of_onset_symptoms"].dt.to_period("W").dt.start_time)
            .groupby("week")
            .size()
            .reset_index(name="cases")
        )
        fig = px.bar(weekly, x="week", y="cases", labels={"week": "Onset week", "cases": "Cases"})
        fig.update_traces(marker_color=who.WHO_BLUE)
        st.plotly_chart(who.style_fig(fig), use_container_width=True)
    else:
        st.info("No onset dates available for the current filter.")

with right:
    st.subheader("Local vs imported")
    if "local_or_imported" in fdf:
        counts = fdf["local_or_imported"].fillna("Unknown").value_counts().reset_index()
        counts.columns = ["local_or_imported", "cases"]
        fig = px.pie(counts, names="local_or_imported", values="cases", hole=0.5)
        st.plotly_chart(who.style_fig(fig, height=360), use_container_width=True)

st.caption(
    f"Showing {len(fdf):,} of {len(df):,} cases after filters. "
    "Use the sidebar to filter; navigate detailed views from the pages menu."
)
