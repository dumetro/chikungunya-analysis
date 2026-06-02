"""Clinical profile: symptoms, comorbidities, PCR positivity, outcomes."""

from __future__ import annotations

import plotly.express as px
import streamlit as st

from data_access import apply_filters, explode_multivalue, load_cases
from filters import sidebar_filters
from theme import who_style as who

st.set_page_config(page_title="Clinical", page_icon="🩺", layout="wide")
who.apply_theme()
who.header("Clinical Profile", "Symptoms, comorbidities, laboratory results and outcomes")

df = load_cases()
fdf = apply_filters(df, sidebar_filters(df))

c1, c2 = st.columns(2)
with c1:
    st.subheader("Symptom frequency")
    sym = explode_multivalue(fdf, "symptoms").head(15)
    if not sym.empty:
        fig = px.bar(sym, x="count", y="symptoms", orientation="h")
        fig.update_traces(marker_color=who.WHO_BLUE)
        fig.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(who.style_fig(fig), use_container_width=True)
    else:
        st.info("No symptom data for current filter.")
with c2:
    st.subheader("Comorbidities")
    com = explode_multivalue(fdf, "comorbidities_pmh").head(15)
    if not com.empty:
        fig = px.bar(com, x="count", y="comorbidities_pmh", orientation="h")
        fig.update_traces(marker_color=who.WHO_RED)
        fig.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(who.style_fig(fig), use_container_width=True)
    else:
        st.info("No comorbidity data for current filter.")

st.divider()
c3, c4 = st.columns(2)
with c3:
    st.subheader("PCR result")
    if "pcr_result" in fdf:
        pcr = fdf["pcr_result"].fillna("Not tested").value_counts().reset_index()
        pcr.columns = ["pcr_result", "cases"]
        fig = px.pie(pcr, names="pcr_result", values="cases", hole=0.45)
        st.plotly_chart(who.style_fig(fig, height=380), use_container_width=True)
with c4:
    st.subheader("Outcome")
    if "outcome" in fdf:
        out = fdf["outcome"].fillna("Unknown").value_counts().reset_index()
        out.columns = ["outcome", "cases"]
        fig = px.bar(out, x="outcome", y="cases")
        fig.update_traces(marker_color=who.WHO_GREEN)
        st.plotly_chart(who.style_fig(fig, height=380), use_container_width=True)
