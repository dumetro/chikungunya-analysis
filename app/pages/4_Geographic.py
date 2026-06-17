"""Geographic distribution: health region, locality, local vs imported."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data_access import REGION_TO_DISTRICT, apply_filters, load_cases
from filters import sidebar_filters
from theme import who_style as who

st.set_page_config(page_title="Geographic", page_icon="🗺️", layout="wide")
who.apply_theme()
who.top_nav(active="Geographic")
who.header("Geographic Distribution", "Cases by health region, locality and origin",
           eyebrow="Where")

# REGION_TO_DISTRICT (MoH health region -> district, matching the geojson
# `province` field) is shared from data_access. health_region is the surveillance
# zone; health_office is a referral/testing hub, not a reliable geographic key.
GEOJSON_PATH = Path(__file__).resolve().parents[2] / "data" / "geodata" / "mauritius_adm1.json"


@st.cache_data(show_spinner=False)
def _load_geojson(path: str) -> dict | None:
    p = Path(path)
    return json.loads(p.read_text()) if p.exists() else None


df = load_cases()
fdf = apply_filters(df, sidebar_filters(df))

# --- Choropleth: cases by district ----------------------------------------
who.section("Case map by district", "Geographic intensity")
CLS_ORDER = ["Confirmed", "Probable", "Suspected", "Unclassified"]
CLS_MARKER = {"Confirmed": "🔴", "Probable": "🟠", "Suspected": "🔵",
              "Unclassified": "⚪"}
OUTER_ISLANDS = {"CARGADOS CARAJOS)", "ÎLE RODRIGUES", "ÎLES AGALÉGA"}


def _centroid(geom: dict) -> tuple[float, float]:
    """Lon/lat centroid of a feature's largest ring (for label placement)."""
    rings = ([geom["coordinates"][0]] if geom["type"] == "Polygon"
             else [poly[0] for poly in geom["coordinates"]])
    ring = max(rings, key=len)
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    return sum(xs) / len(xs), sum(ys) / len(ys)


geo = _load_geojson(str(GEOJSON_PATH))
if geo is None:
    st.info(f"District boundaries not found at {GEOJSON_PATH.name}. "
            "Add the GeoJSON to data/geodata/ to enable the map.")
elif "health_region" in fdf.columns and not fdf.empty:
    mainland = [f["properties"]["province"] for f in geo["features"]
                if f["properties"]["province"] not in OUTER_ISLANDS]
    mdf = fdf.copy()
    mdf["district"] = mdf["health_region"].map(REGION_TO_DISTRICT)
    mdf["case_classification"] = mdf["case_classification"].fillna("Unclassified")
    # Counts per district x classification, every mainland district present (0-filled).
    ct = (pd.crosstab(mdf["district"], mdf["case_classification"])
          .reindex(index=mainland, columns=CLS_ORDER, fill_value=0)
          .fillna(0).astype(int))
    ct["total"] = ct[CLS_ORDER].sum(axis=1)
    agg = ct.reset_index()

    # Choroplethmapbox (NOT the geo choropleth, which mis-fills these polygons
    # due to ring winding order). White basemap + white→red scale so zero
    # districts read as white; per-classification breakdown lives in the hover.
    fig = go.Figure(go.Choroplethmapbox(
        geojson=geo, locations=agg["district"], featureidkey="properties.province",
        z=agg["total"], zmin=0, zmax=int(agg["total"].max()) or 1,
        colorscale=[[0, "#ffffff"], [0.25, "#FEB24C"], [0.6, "#FC4E2A"],
                    [1, "#BD0026"]],
        customdata=agg[CLS_ORDER].to_numpy(),
        marker_line_color="#3a3a3a", marker_line_width=1,
        colorbar=dict(title="Cases"),
        hovertemplate=(
            "<b>%{location}</b><br>Total: %{z}<br>"
            "🔴 Confirmed: %{customdata[0]}<br>🟠 Probable: %{customdata[1]}<br>"
            "🔵 Suspected: %{customdata[2]}<br>⚪ Unclassified: %{customdata[3]}"
            "<extra></extra>"),
    ))
    # On-map labels: district name only (counts are in the hover tooltip).
    lons, lats, names = [], [], []
    for feat in geo["features"]:
        name = feat["properties"]["province"]
        if name not in mainland:
            continue
        lon, lat = _centroid(feat["geometry"])
        lons.append(lon)
        lats.append(lat)
        names.append(name.title())
    fig.add_trace(go.Scattermapbox(
        lon=lons, lat=lats, text=names, mode="text",
        textfont=dict(size=11, color="#111111"),
        showlegend=False, hoverinfo="skip",
    ))
    fig.update_layout(
        mapbox_style="white-bg",
        mapbox_center={"lat": -20.28, "lon": 57.55}, mapbox_zoom=9.2,
        margin=dict(l=0, r=0, t=0, b=0), height=620,
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "District shading = total reported cases (white = none). Hover a district "
        "for the classification breakdown (Confirmed / Probable / Suspected / "
        "Unclassified). Moka and Regions 6–8 (Savanne, Black River, Plaines "
        "Wilhems) have no cases yet.")
    who.notes(
        "Choropleth of total reported cases by district, with the classification "
        "breakdown on hover.",
        "Cases are placed via the `health_region`→district mapping onto the "
        "bundled Mauritius GeoJSON, so it needs `health_region` populated. Only "
        "Regions 1–5 have data today (others render white/0). If health-region "
        "definitions or the boundary file change, update `REGION_TO_DISTRICT` / "
        "the GeoJSON. This is region-of-report, not residence.")
else:
    st.info("Needs the health_region column — not available for the current filter.")

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
