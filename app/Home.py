"""Chikungunya Outbreak Surveillance Dashboard — overview / landing page.

Run with:  streamlit run app/Home.py
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from data_access import (
    apply_filters,
    epi_week_classification_counts,
    epi_week_counts,
    kpi_summary,
    load_cases,
)
from filters import sidebar_filters
from theme import who_style as who

st.set_page_config(page_title="Chikungunya Surveillance", page_icon="🦟", layout="wide")
who.apply_theme()
who.top_nav(active="Overview")

who.header(
    "Chikungunya Outbreak Surveillance",
    f"Case-level analysis dashboard · data as of {date.today().isoformat()}",
    eyebrow="WHO Surveillance Dashboard",
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

# --- Epidemic curve by epi week (full width) -------------------------------
# Stacked: Confirmed (case_classification == 'Confirmed') + Suspected (everything
# else). The two segments sum to the weekly total (shown by the line markers).
who.section("Epidemic curve — suspected vs confirmed by epi week", "Epi curve")
stack_df = epi_week_classification_counts(fdf)
week_df = epi_week_counts(fdf)  # weekly totals for the trend line
if not stack_df.empty:
    fig = px.bar(
        stack_df, x="epi_week", y="cases", color="Classification",
        barmode="stack",
        category_orders={"Classification": ["Suspected", "Confirmed"]},
        color_discrete_map={"Suspected": who.WHO_BLUE, "Confirmed": who.WHO_RED},
        labels={"epi_week": "Epi week", "cases": "Cases"},
    )
    # Total trend line with weekly count labels (= top of each stack).
    fig.add_scatter(
        x=week_df["epi_week"], y=week_df["cases"],
        mode="lines+markers+text",
        text=week_df["cases"],
        texttemplate="%{text}",
        textposition="top center",
        line=dict(color=who.WHO_DARK, width=2),
        marker=dict(color=who.WHO_DARK, size=7),
        name="Weekly total",
        cliponaxis=False,
    )
    # Integer week ticks, axis extends to max(epi_week) in the data.
    fig.update_xaxes(dtick=1, range=[week_df["epi_week"].min() - 0.5,
                                     week_df["epi_week"].max() + 0.5])
    st.plotly_chart(who.style_fig(fig, height=440), use_container_width=True)
    confirmed_total = int(stack_df.loc[stack_df["Classification"] == "Confirmed", "cases"].sum())
    total = int(stack_df["cases"].sum())
    st.caption(
        f"{total:,} total cases ({confirmed_total:,} confirmed, {total - confirmed_total:,} "
        f"suspected) across epi weeks {int(week_df['epi_week'].min())}–"
        f"{int(week_df['epi_week'].max())}."
    )
else:
    st.info("No epi week data available for the current filter.")

st.divider()

# --- Epi curve preview -----------------------------------------------------
left, right = st.columns([2, 1])
with left:
    who.section("Suspected vs confirmed cases by region", "Classification")
    if {"health_region", "case_classification"} <= set(fdf.columns):
        sub = fdf.copy()
        sub["health_region"] = sub["health_region"].fillna("Unknown")
        # Suspected = all uploaded rows per region; Confirmed = classification == 'Confirmed'.
        suspected = sub.groupby("health_region").size().rename("Suspected")
        confirmed = (sub[sub["case_classification"] == "Confirmed"]
                     .groupby("health_region").size().rename("Confirmed"))
        agg = pd.concat([suspected, confirmed], axis=1).fillna(0).astype(int)
        if not agg.empty:
            order = agg.sort_values("Suspected", ascending=False).index.tolist()
            long = (agg.reset_index()
                    .melt(id_vars="health_region", value_vars=["Suspected", "Confirmed"],
                          var_name="Classification", value_name="cases"))
            fig = px.bar(
                long, x="health_region", y="cases", color="Classification",
                barmode="group",
                category_orders={"health_region": order,
                                 "Classification": ["Suspected", "Confirmed"]},
                color_discrete_map={"Suspected": who.WHO_BLUE, "Confirmed": who.WHO_RED},
                labels={"health_region": "Health region", "cases": "Cases"},
            )
            st.plotly_chart(who.style_fig(fig), use_container_width=True)
        else:
            st.info("No cases for the current filter.")
    else:
        st.info("Region or classification data not available.")

with right:
    who.section("Local vs imported", "Transmission")
    if "local_or_imported" in fdf:
        counts = fdf["local_or_imported"].fillna("Unknown").value_counts().reset_index()
        counts.columns = ["local_or_imported", "cases"]
        fig = px.pie(counts, names="local_or_imported", values="cases", hole=0.5)
        st.plotly_chart(who.style_fig(fig, height=360), use_container_width=True)

st.caption(
    f"Showing {len(fdf):,} of {len(df):,} cases after filters. "
    "Use the sidebar to filter; navigate detailed views from the pages menu."
)
