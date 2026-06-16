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
    parse_epi_week,
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
who.section("Epidemic curve: suspected vs confirmed by epi week", "Epi curve")
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

# --- Classification mix over time (100% stacked area) ----------------------
# Proportion of each WHO/PAHO classification per epi week, to surface shifts in
# the case mix (e.g. rising confirmed share) over the outbreak.
who.section("Classification mix by epi week", "Proportion over time")
if {"epi_week", "case_classification"} <= set(fdf.columns):
    cls_order = ["Confirmed", "Probable", "Suspected", "Unclassified"]
    cls_colors = {"Confirmed": who.WHO_RED, "Probable": who.WHO_AMBER,
                  "Suspected": who.WHO_BLUE, "Unclassified": who.WHO_GREY}
    d = fdf.copy()
    d["_wk"] = d["epi_week"].map(parse_epi_week)
    d = d.dropna(subset=["_wk"])
    if not d.empty:
        d["_wk"] = d["_wk"].astype(int)
        d["case_classification"] = d["case_classification"].fillna("Unclassified")
        wide = d.groupby(["_wk", "case_classification"]).size().unstack(fill_value=0)
        extras = [c for c in wide.columns if c not in cls_order]
        cols = [c for c in cls_order if c in wide.columns] + extras
        wide = wide[cols]
        # Per-week proportion (%). Only observed weeks are kept, so missing weeks
        # don't read as a false drop to 0%.
        pct = wide.div(wide.sum(axis=1), axis=0).fillna(0) * 100
        long = (pct.reset_index(names="epi_week")
                .melt(id_vars="epi_week", var_name="Classification", value_name="pct"))
        fig = px.area(
            long, x="epi_week", y="pct", color="Classification",
            category_orders={"Classification": cols},
            color_discrete_map=cls_colors,
            labels={"epi_week": "Epi week", "pct": "% of cases"},
        )
        fig.update_yaxes(range=[0, 100], ticksuffix="%")
        fig.update_xaxes(dtick=1)
        st.plotly_chart(who.style_fig(fig, height=420), use_container_width=True)
        st.caption(
            f"Share of each classification per epi week across weeks "
            f"{int(d['_wk'].min())}–{int(d['_wk'].max())} "
            f"({len(d):,} dated cases). Each week's bands sum to 100%.")
    else:
        st.info("No dated cases for the current filter.")
else:
    st.info("Epi week or classification data not available.")

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

st.divider()

# --- Locality hotspot ranking ----------------------------------------------
# Ranks localities by reported burden, split into Suspected (all reported
# cases) and Confirmed (case_classification == 'Confirmed'), matching the
# region chart's convention. Drives where to focus vector control.
who.section("Locality hotspots: suspected vs confirmed", "Where to act")
TOP_N = 15
if {"locality", "case_classification"} <= set(fdf.columns) and not fdf.empty:
    sub = fdf.copy()
    sub["locality"] = sub["locality"].fillna("Unknown")
    suspected = sub.groupby("locality").size().rename("Suspected")
    confirmed = (sub[sub["case_classification"] == "Confirmed"]
                 .groupby("locality").size().rename("Confirmed"))
    agg = (pd.concat([suspected, confirmed], axis=1).fillna(0).astype(int)
           .sort_values("Suspected", ascending=False).head(TOP_N))
    if not agg.empty:
        order = agg.index.tolist()
        long = (agg.reset_index()
                .melt(id_vars="locality", value_vars=["Suspected", "Confirmed"],
                      var_name="Classification", value_name="cases"))
        fig = px.bar(
            long, x="cases", y="locality", color="Classification",
            barmode="group", orientation="h",
            category_orders={"locality": order,
                             "Classification": ["Suspected", "Confirmed"]},
            color_discrete_map={"Suspected": who.WHO_BLUE, "Confirmed": who.WHO_RED},
            labels={"locality": "Locality", "cases": "Cases"},
        )
        fig.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(who.style_fig(fig, height=540), use_container_width=True)
        st.caption(
            f"Top {TOP_N} of {sub['locality'].nunique():,} localities by reported "
            "burden. Suspected = all reported cases; Confirmed = confirmed subset.")
        who.callout(
            "<b>Guiding entomological surveillance &amp; intervention:</b> the "
            "highest-ranked localities are where human transmission is most "
            "intense, so they are first-priority for <i>Aedes</i> vector work — "
            "larval/pupal and adult (BG-trap/ovitrap) surveys to map breeding "
            "foci, and targeted source reduction, larviciding and space-spraying "
            "around confirmed clusters. A high <i>confirmed</i> share signals "
            "verified active transmission warranting immediate vector response; "
            "a large <i>suspected</i> burden with few confirmations flags "
            "localities needing strengthened sampling/lab follow-up before "
            "committing scarce control resources. Re-checking this ranking each "
            "epi week shows whether interventions are reducing local burden.",
            "info")
    else:
        st.info("No locality cases for the current filter.")
else:
    st.info("Locality or classification data not available.")

st.divider()
st.caption(
    f"Showing {len(fdf):,} of {len(df):,} cases after filters. "
    "Use the sidebar to filter; navigate detailed views from the pages menu."
)
