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
    pyr = (
        fdf.dropna(subset=["age_group"])
        .groupby(["age_group", "gender"]).size().reset_index(name="count")
    )
    order = sorted(pyr["age_group"].unique(), key=lambda s: (len(s), s))
    male = pyr[pyr["gender"] == "Male"].set_index("age_group")["count"].reindex(order).fillna(0)
    female = pyr[pyr["gender"] == "Female"].set_index("age_group")["count"].reindex(order).fillna(0)
    fig = go.Figure()
    fig.add_bar(y=order, x=-male.values, name="Male", orientation="h", marker_color=who.WHO_BLUE)
    fig.add_bar(y=order, x=female.values, name="Female", orientation="h", marker_color=who.WHO_AMBER)
    fig.update_layout(barmode="relative", title="Cases by age group and sex",
                      xaxis_title="Male  ←   cases   →  Female")
    fig.update_xaxes(tickvals=[-male.max(), 0, female.max()],
                     ticktext=[int(male.max()), 0, int(female.max())])
    st.plotly_chart(who.style_fig(fig, height=480), use_container_width=True)
else:
    st.info("Age group / gender not available for current filter.")

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
with c2:
    st.subheader("Occupation")
    if "occupation" in fdf:
        occ = fdf["occupation"].fillna("Unknown").value_counts().head(12).reset_index()
        occ.columns = ["occupation", "cases"]
        fig = px.bar(occ, x="cases", y="occupation", orientation="h")
        fig.update_traces(marker_color=who.WHO_PURPLE)
        fig.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(who.style_fig(fig), use_container_width=True)
