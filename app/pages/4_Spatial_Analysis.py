"""Spatial analysis: interactive outbreak map, health region, locality, origin."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components

from data_access import apply_filters, load_cases
from filters import sidebar_filters
from spatial_map import build_map_html
from theme import who_style as who

st.set_page_config(page_title="Spatial Analysis", page_icon="🗺️", layout="wide")
who.apply_theme()
who.top_nav(active="Spatial Analysis")
who.header("Spatial Analysis", "Interactive outbreak map, cases by region, locality and origin",
           eyebrow="Where")

GEODATA = Path(__file__).resolve().parents[2] / "data" / "geodata"


@st.cache_data(show_spinner="Building interactive map …")
def _interactive_map_html() -> str:
    return build_map_html(str(GEODATA))


df = load_cases()
fdf = apply_filters(df, sidebar_filters(df))

# --- Interactive outbreak map (Leaflet + OpenStreetMap base) ---------------
# The full Earth-AI dashboard, rebuilt from the bundled geodata layers: a
# CARTO/OpenStreetMap base map with toggleable overlays (case-intensity
# choropleth, graduated case-volume symbols, Aedes hotspots and the Aug–Oct
# expansion-risk forecast), a following legend and headline stat cards.
who.section("Interactive outbreak map", "All layers · OpenStreetMap base map")
components.html(_interactive_map_html(), height=780, scrolling=False)
st.caption(
    "Interactive Leaflet map over an OpenStreetMap (CARTO) base map. Toggle "
    "layers with the control at the top-right: district case-intensity "
    "choropleth, graduated case-volume symbols, *Aedes albopictus* vector "
    "hotspots, and the August–October 2026 expansion-risk forecast. Click any "
    "district, symbol or marker for detail. Fixed July-2026 geodata snapshot "
    "(`data/geodata/`, generated with Google Earth AI) — independent of the "
    "sidebar filter.")
who.notes(
    "The interactive outbreak dashboard: an OpenStreetMap-based map with the "
    "case-intensity choropleth, graduated case symbols, Aedes vector hotspots "
    "and the 3-month expansion-risk forecast as switchable layers, plus a legend "
    "and headline indicators.",
    "Renders the bundled `data/geodata/` GeoJSON layers inside an embedded "
    "Leaflet view (Leaflet + CARTO/OSM tiles load from CDN — needs network). It "
    "is a fixed July-2026 snapshot and does not respond to the sidebar filter; "
    "the live charts below do. Update the geodata layers to refresh it.")

st.divider()

st.subheader("Cases by health region")
if "health_region" in fdf:
    reg = fdf["health_region"].fillna("Unknown").value_counts().reset_index()
    reg.columns = ["health_region", "cases"]
    fig = px.bar(reg, x="health_region", y="cases", color="cases",
                 color_continuous_scale=who.SEQUENTIAL_BLUE)
    st.plotly_chart(who.style_fig(fig), use_container_width=True)
    who.notes(
        "Raw case counts per health-region label (Region 1–N), without mapping "
        "to geography.",
        "Requires `health_region` populated; uses the labels exactly as recorded "
        "('Unknown' = blank). New regions appear automatically as they enter the "
        "data — no code change needed.")

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
        who.notes(
            "The 15 localities with the most cases.",
            "Uses `locality` as recorded (currently fully populated, ~150 "
            "distinct). These are case-*burden* counts, not incidence — populous "
            "localities rank high regardless of risk; a per-capita view would need "
            "locality population denominators.")
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
        who.notes(
            "Local vs imported case mix within each health region.",
            "Needs `local_or_imported` populated; today it is almost entirely "
            "'Local' with no 'Imported' recorded, so this becomes informative only "
            "once importation status is captured at source ('Unknown' = blank).")

st.divider()
who.section("Case classification by health region",
            "Health region × WHO/PAHO classification")
if {"health_region", "case_classification"} <= set(fdf.columns) and not fdf.empty:
    order = ["Confirmed", "Probable", "Suspected", "Unclassified"]
    ct = pd.crosstab(
        fdf["health_region"].fillna("Unknown"),
        fdf["case_classification"].fillna("Unclassified"),
    )
    # canonical column order first, then any unexpected extras
    cols = [c for c in order if c in ct.columns] + \
           [c for c in ct.columns if c not in order]
    ct = ct[cols]
    ct = ct.loc[ct.sum(axis=1).sort_values(ascending=False).index]  # busiest region on top
    fig = px.imshow(
        ct, text_auto=True, aspect="auto",
        color_continuous_scale=["#FFEDA0", "#FEB24C", "#FC4E2A", "#BD0026"],
        labels=dict(x="Classification", y="Health region", color="Cases"),
    )
    fig.update_xaxes(side="top")
    st.plotly_chart(who.style_fig(fig, height=80 + 52 * len(ct)),
                    use_container_width=True)
    st.caption("Case counts per health region and classification for the current "
               "filter. Region labels are as recorded in the source data.")
    who.notes(
        "Case counts cross-tabulated by health region and WHO/PAHO classification "
        "— a quick read of where confirmed vs suspected burden sits.",
        "Requires `health_region` and the derived `case_classification`. Region "
        "labels are the raw 'Region N' values (not districts). Cells shift as "
        "pending PCR results resolve and reclassify cases.")
else:
    st.info("Needs the health_region and case_classification columns — "
            "not available for the current filter.")
