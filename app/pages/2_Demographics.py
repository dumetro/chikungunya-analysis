"""Demographics: age-sex pyramid, age groups, nationality, occupation."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from data_access import apply_filters, load_cases
from filters import sidebar_filters
from theme import who_style as who

st.set_page_config(page_title="Demographics", page_icon="👥", layout="wide")
who.apply_theme()
who.top_nav(active="Demographics")
who.header("Demographics", "Age, sex, nationality and occupation distribution",
           eyebrow="Who Is Affected")

df = load_cases()
fdf = apply_filters(df, sidebar_filters(df))

# --- Age-sex pyramid -------------------------------------------------------
st.subheader("Age–sex pyramid")
if {"age_group", "gender"} <= set(fdf.columns) and fdf["age_group"].notna().any():
    CLS_ORDER = ["Confirmed", "Probable", "Suspected", "Unclassified"]
    CLS_COLORS = {"Confirmed": who.WHO_RED, "Probable": who.WHO_AMBER,
                  "Suspected": who.WHO_BLUE, "Unclassified": who.WHO_GREY}
    pyr = fdf.dropna(subset=["age_group"]).copy()
    pyr["case_classification"] = pyr["case_classification"].fillna("Unclassified")
    grp = pyr.groupby(["age_group", "gender", "case_classification"]).size()
    order = sorted(pyr["age_group"].unique(), key=lambda s: (len(s), s))

    fig = go.Figure()
    # Male on the left (negative x), Female on the right; each side stacked by
    # classification. Legend shown once per classification (female side) and
    # grouped so a click toggles both sides together.
    for side, gender, sign, show in (("M", "Male", -1, False), ("F", "Female", 1, True)):
        for cls in CLS_ORDER:
            vals = [int(grp.get((ag, gender, cls), 0)) for ag in order]
            fig.add_bar(
                y=order, x=[sign * v for v in vals], name=cls, orientation="h",
                marker_color=CLS_COLORS[cls], legendgroup=cls, showlegend=show,
                customdata=vals,
                hovertemplate=f"{gender} · {cls}<br>%{{y}}: %{{customdata}} cases<extra></extra>",
            )
    male_tot = max((sum(int(grp.get((ag, "Male", c), 0)) for c in CLS_ORDER) for ag in order), default=0)
    female_tot = max((sum(int(grp.get((ag, "Female", c), 0)) for c in CLS_ORDER) for ag in order), default=0)
    fig.update_layout(barmode="relative",
                      title=dict(text="Cases by age group, sex and classification",
                                 x=0, xanchor="left"),
                      xaxis_title="Male  ←   cases   →  Female",
                      legend=dict(orientation="h", yanchor="top", y=-0.18,
                                  xanchor="center", x=0.5, title_text=""))
    fig.update_xaxes(tickvals=[-male_tot, 0, female_tot],
                     ticktext=[male_tot, 0, female_tot])
    st.plotly_chart(who.style_fig(fig, height=480), use_container_width=True)
    who.notes(
        "Population structure of cases — counts by age group and sex (male left, "
        "female right), each side stacked by WHO/PAHO classification.",
        "Requires `age_group` (the pipeline derives it from `age` into canonical "
        "bands when the band is missing) and `gender` standardised to "
        "Male/Female; rows missing either are excluded, so completeness of age "
        "and sex at source drives accuracy. Segment sizes depend on the derived "
        "`case_classification`.")
else:
    st.info("Age group / gender not available for current filter.")

# --- Cases by gender -------------------------------------------------------
st.subheader("Cases by gender")
if "gender" in fdf.columns and fdf["gender"].notna().any():
    gen = fdf["gender"].fillna("Unknown").value_counts().reset_index()
    gen.columns = ["gender", "cases"]
    fig = px.pie(gen, names="gender", values="cases", hole=0.5,
                 color="gender",
                 color_discrete_map={"Male": who.WHO_BLUE, "Female": who.WHO_AMBER,
                                     "Unknown": who.WHO_GREY})
    fig.update_traces(textinfo="label+percent")
    st.plotly_chart(who.style_fig(fig, height=380), use_container_width=True)
    who.notes(
        "Share of cases by sex.",
        "`gender` is standardised to Male/Female during sanitisation; blank or "
        "unrecognised values show as 'Unknown'. Accuracy just needs sex recorded "
        "at source.")
else:
    st.info("Gender not available for current filter.")

c1, c2 = st.columns(2)
with c1:
    st.subheader("Nationality")
    if "nationality" in fdf:
        nat = fdf["nationality"].fillna("Unknown").value_counts().head(12).reset_index()
        nat.columns = ["nationality", "cases"]
        fig = px.bar(nat, x="cases", y="nationality", orientation="h")
        fig.update_traces(marker_color=who.WHO_TEAL)
        fig.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(who.style_fig(fig), use_container_width=True)
        who.notes(
            "The 12 most frequent nationalities among cases ('Unknown' = blank).",
            "`nationality` is normalised against the reference table; values not "
            "yet mapped keep their cleaned raw form and can split one nationality "
            "across spellings. When the unmapped-values report flags new variants, "
            "add them to the nationality reference / raw map and re-run.")
with c2:
    st.subheader("Occupation")
    if "occupation" in fdf:
        occ = fdf["occupation"].fillna("Unknown").value_counts().head(12).reset_index()
        occ.columns = ["occupation", "cases"]
        fig = px.bar(occ, x="cases", y="occupation", orientation="h")
        fig.update_traces(marker_color=who.WHO_PURPLE)
        fig.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(who.style_fig(fig), use_container_width=True)
        who.notes(
            "The 12 most frequent occupations among cases ('Unknown' = blank).",
            "`occupation` is normalised via `occupation_raw_map`; unmapped "
            "free-text occupations stay as-is and fragment the counts until added "
            "to the raw map. Extend the map from the unmapped-values report, then "
            "re-run the pipeline.")
