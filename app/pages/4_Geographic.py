"""Geographic distribution: health region, locality, local vs imported."""

from __future__ import annotations

import plotly.express as px
import streamlit as st

from data_access import apply_filters, load_cases
from filters import sidebar_filters
from theme import who_style as who

st.set_page_config(page_title="Geographic", page_icon="🗺️", layout="wide")
who.apply_theme()
who.top_nav(active="Geographic")
who.header("Geographic Distribution", "Cases by health region, locality and origin",
           eyebrow="Where")

df = load_cases()
fdf = apply_filters(df, sidebar_filters(df))

st.subheader("Cases by health region")
if "health_region" in fdf:
    reg = fdf["health_region"].fillna("Unknown").value_counts().reset_index()
    reg.columns = ["health_region", "cases"]
    fig = px.bar(reg, x="health_region", y="cases", color="cases",
                 color_continuous_scale=who.SEQUENTIAL_BLUE)
    st.plotly_chart(who.style_fig(fig), use_container_width=True)

c1, c2 = st.columns(2)
with c1:
    st.subheader("Top localities")
    if "locality" in fdf:
        loc = fdf["locality"].fillna("Unknown").value_counts().head(15).reset_index()
        loc.columns = ["locality", "cases"]
        fig = px.bar(loc, x="cases", y="locality", orientation="h")
        fig.update_traces(marker_color=who.WHO_TEAL)
        fig.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(who.style_fig(fig, height=460), use_container_width=True)
with c2:
    st.subheader("Local vs imported by region")
    if {"health_region", "local_or_imported"} <= set(fdf.columns):
        grp = (
            fdf.assign(local_or_imported=fdf["local_or_imported"].fillna("Unknown"),
                       health_region=fdf["health_region"].fillna("Unknown"))
            .groupby(["health_region", "local_or_imported"]).size().reset_index(name="cases")
        )
        fig = px.bar(grp, x="health_region", y="cases", color="local_or_imported",
                     barmode="stack")
        st.plotly_chart(who.style_fig(fig, height=460), use_container_width=True)
