"""Geographic distribution: health region, locality, local vs imported."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data_access import apply_filters, load_cases
from filters import sidebar_filters
from theme import who_style as who

st.set_page_config(page_title="Geographic", page_icon="🗺️", layout="wide")
who.apply_theme()
who.top_nav(active="Geographic")
who.header("Geographic Distribution", "Cases by health region, locality and origin",
           eyebrow="Where")

GEODATA = Path(__file__).resolve().parents[2] / "data" / "geodata"


@st.cache_data(show_spinner=False)
def _load_geojson(path: str) -> dict | None:
    p = Path(path)
    return json.loads(p.read_text()) if p.exists() else None


df = load_cases()
fdf = apply_filters(df, sidebar_filters(df))

# --- Graduated-symbol map: district case volume -----------------------------
# Renders the curated July-2026 geodata layers (data/geodata/): a graduated
# symbol per district, area-proportional to case volume, over district outlines
# with name+count labels. This uses the locality-geocoded district attribution
# baked into the geodata rather than the health_region→district surveillance
# mapping (health_region is the reporting zone, not residence).
who.section("Case map by district", "Graduated symbols — outbreak intensity")

OUTER_ISLANDS = {"Agaléga", "Saint Brandon", "Rodrigues"}
# Earth-AI-style glow palette: translucent bubbles with bright cores over a
# satellite basemap, with lavender district outlines. Bubbles are coloured by
# case intensity on a red → orange → yellow ramp.
INTENSITY_COLOR = {
    "Very High": "#E8112D",   # red
    "High": "#FF5A00",        # orange-red
    "Moderate": "#FF9500",    # orange
    "Low": "#FFC400",         # amber
    "Minimal": "#FFE873",     # yellow
}
CORE_HALO = "#FFF3D6"     # warm-white halo behind each core
PIN = "#FFFFFF"           # bright core pin
LABEL = "#FFF3D6"         # on-map label text
OUTLINE = "rgba(206,168,255,0.72)"   # lavender district boundaries


def _intensity_color(intensity: str | None, cases: int, max_cases: int) -> str:
    """Red→orange→yellow by intensity class, falling back to case-volume bins."""
    if intensity in INTENSITY_COLOR:
        return INTENSITY_COLOR[intensity]
    frac = cases / max_cases if max_cases else 0
    return "#E8112D" if frac >= 0.6 else "#FF9500" if frac >= 0.25 else "#FFC400"
# ESRI World Imagery satellite tiles — no Mapbox token required.
_SAT_LAYER = {
    "below": "traces", "sourcetype": "raster", "sourceattribution": "Esri, Maxar",
    "source": ["https://server.arcgisonline.com/ArcGIS/rest/services/"
               "World_Imagery/MapServer/tile/{z}/{y}/{x}"],
}
# Concentric glow layers per district: (diameter × factor, opacity), faint+wide
# to opaque+tight, so overlap builds a soft radial gradient toward the centre.
_GLOW_LAYERS = [(2.2, 0.06), (1.7, 0.11), (1.25, 0.23), (1.0, 0.50)]


def _polylines(geom: dict | None):
    """Yield (lons, lats) for each part of a LineString / MultiLineString."""
    if not geom:
        return
    segs = ([geom["coordinates"]] if geom["type"] == "LineString"
            else geom["coordinates"] if geom["type"] == "MultiLineString" else [])
    for seg in segs:
        yield [p[0] for p in seg], [p[1] for p in seg]


symbols = _load_geojson(str(GEODATA / "district_case_volume__graduated_symbols_.geojson"))
outlines = _load_geojson(str(GEODATA / "district_boundaries__outlines_only_.geojson"))
labels = _load_geojson(str(GEODATA / "district_labels__names_and_case_counts_.geojson"))

if symbols is None:
    st.info("Graduated-symbol geodata not found. Add "
            "district_case_volume__graduated_symbols_.geojson to data/geodata/.")
else:
    # District centroids (from the labels layer) anchor both bubbles and labels.
    centroid = {f["properties"]["name"]: f["geometry"]["coordinates"]
                for f in (labels or {}).get("features", []) if f.get("geometry")}

    # Mainland districts with cases.
    rows = []  # (intensity, name, cases, lon, lat)
    for feat in symbols["features"]:
        p = feat["properties"]
        name = p["name"]
        if name in OUTER_ISLANDS or int(p.get("cases", 0)) <= 0:
            continue
        lonlat = centroid.get(name)
        if not lonlat:
            continue
        display = name.replace(" District", "").strip()
        rows.append((p.get("intensity", "Minimal"), display, int(p["cases"]),
                     lonlat[0], lonlat[1]))

    fig = go.Figure()

    # 1) District outlines (lavender), beneath the glow.
    if outlines:
        olon, olat = [], []
        for feat in outlines["features"]:
            if feat["properties"]["name"] in OUTER_ISLANDS:
                continue
            for lons, lats in _polylines(feat["geometry"]):
                olon += lons + [None]
                olat += lats + [None]
        fig.add_trace(go.Scattermapbox(
            lon=olon, lat=olat, mode="lines", line=dict(color=OUTLINE, width=1.3),
            hoverinfo="skip", showlegend=False))

    # 2) Graduated glow symbols. Body diameter (px) is √-scaled to case volume;
    #    stacked translucent teal layers + a bright core give the Earth-AI glow.
    if rows:
        max_cases = max(r[2] for r in rows)
        lons = [r[3] for r in rows]
        lats = [r[4] for r in rows]
        cols = [_intensity_color(r[0], r[2], max_cases) for r in rows]
        body = [max(28.0, min(104.0, (r[2] / max_cases) ** 0.5 * 104.0)) for r in rows]
        core = [max(9.0, min(18.0, d * 0.22)) for d in body]

        for factor, op in _GLOW_LAYERS:
            fig.add_trace(go.Scattermapbox(
                lon=lons, lat=lats, mode="markers",
                marker=dict(size=[d * factor for d in body], color=cols, opacity=op),
                hoverinfo="skip", showlegend=False))

        # warm-white halo behind the cores, for the bright bloom
        fig.add_trace(go.Scattermapbox(
            lon=lons, lat=lats, mode="markers",
            marker=dict(size=[c * 2.2 for c in core], color=CORE_HALO, opacity=0.55),
            hoverinfo="skip", showlegend=False))
        # bright core pin — carries the hover tooltip
        fig.add_trace(go.Scattermapbox(
            lon=lons, lat=lats, mode="markers",
            marker=dict(size=[max(5.0, c * 0.9) for c in core], color=PIN, opacity=0.95),
            customdata=[[r[1], r[2], r[0]] for r in rows],
            hovertemplate=("<b>%{customdata[0]}</b><br>%{customdata[1]:,} cases"
                           "<br>Intensity: %{customdata[2]}<extra></extra>"),
            showlegend=False))
        # labels: district name + count, nudged north of the core (plain text —
        # mapbox labels don't render HTML tags, only <br>)
        fig.add_trace(go.Scattermapbox(
            lon=lons, lat=[la + 0.014 for la in lats], mode="text",
            text=[f"{r[1]}<br>{r[2]:,}" for r in rows],
            textfont=dict(size=11, color=LABEL, family="Arial"),
            hoverinfo="skip", showlegend=False))

    fig.update_layout(
        mapbox_style="white-bg", mapbox_layers=[_SAT_LAYER],
        mapbox_center={"lat": -20.30, "lon": 57.57}, mapbox_zoom=9.55,
        margin=dict(l=0, r=0, t=0, b=0), height=700, showlegend=False,
        paper_bgcolor="#0a0f1c")
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Graduated symbols: bubble **size** ∝ reported case volume per district, "
        "**coloured by case intensity** (🔴 red = Very High → 🟠 orange → 🟡 yellow "
        "= Low), over an Esri satellite basemap. Plaines Wilhems is the red "
        "epicentre. Source: curated July 2026 geodata (`data/geodata/`, generated "
        "with Google Earth AI), locality-geocoded to district — a fixed snapshot, "
        "independent of the sidebar filter. Outer islands (Agaléga, Saint Brandon, "
        "Rodrigues) have no cases and are omitted.")
    who.notes(
        "A graduated-symbol map of district case volume for the July 2026 outbreak "
        "snapshot, styled after the Google Earth AI visualisation: Plaines Wilhems "
        "is the epicentre, with Port Louis and Black River as secondary foci.",
        "Renders the bundled geodata layers (graduated symbols + district outlines "
        "+ labels) generated with Google Earth AI, over Esri World Imagery satellite "
        "tiles (external; needs network). Bubble diameter is √-scaled to `cases` and "
        "the glow is coloured by intensity class on a red→orange→yellow ramp "
        "(stacked translucent layers); hover gives the exact count and class. Fixed "
        "to the geodata snapshot — it does not respond to the sidebar filter (the "
        "live charts below do).")

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
