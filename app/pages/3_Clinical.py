"""Clinical profile: symptoms, comorbidities, PCR positivity, outcomes."""

from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data_access import apply_filters, explode_multivalue, load_cases
from filters import sidebar_filters
from theme import who_style as who

st.set_page_config(page_title="Clinical", page_icon="🩺", layout="wide")
who.apply_theme()
who.top_nav(active="Clinical")
who.header("Clinical Profile", "Symptoms, comorbidities, laboratory results and outcomes",
           eyebrow="Clinical")

df = load_cases()
fdf = apply_filters(df, sidebar_filters(df))

# --- Case classification (WHO/PAHO) ---------------------------------------
if "case_classification" in fdf.columns:
    who.section("Case classification", "WHO / PAHO surveillance definition")
    order = ["Confirmed", "Probable", "Suspected", "Unclassified"]
    counts = (
        fdf["case_classification"].value_counts()
        .reindex(order).dropna().reset_index()
    )
    counts.columns = ["classification", "cases"]
    kpi = fdf["case_classification"].value_counts()
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Confirmed", int(kpi.get("Confirmed", 0)))
    k2.metric("Probable", int(kpi.get("Probable", 0)))
    k3.metric("Suspected", int(kpi.get("Suspected", 0)))
    k4.metric("Unclassified", int(kpi.get("Unclassified", 0)))
    color_map = {"Confirmed": who.WHO_RED, "Probable": who.WHO_AMBER,
                 "Suspected": who.WHO_BLUE, "Unclassified": who.WHO_GREY}
    fig = px.bar(counts, x="classification", y="cases", color="classification",
                 color_discrete_map=color_map)
    fig.update_layout(showlegend=False)
    st.plotly_chart(who.style_fig(fig, height=340), use_container_width=True)
    st.caption("Derived per row from PCR result, epi-linkage and clinical symptoms "
               "(see config/case_definitions.yaml).")

    # Why are rows unclassified? Logged reasons (also recorded in the lineage table).
    n_unc = int(kpi.get("Unclassified", 0))
    if n_unc:
        from chikungunya_pipeline.classify import classify_cases_with_reasons

        _, reasons = classify_cases_with_reasons(fdf)
        reasons = reasons[reasons.astype(bool)]
        with st.expander(f"Why unclassified? ({n_unc} rows)"):
            br = reasons.value_counts().reset_index()
            br.columns = ["reason", "rows"]
            st.dataframe(br, use_container_width=True, hide_index=True)
    st.divider()

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

# --- Transmission chain analysis ------------------------------------------
st.divider()
who.section("Transmission chain analysis",
            "Nationality → health region → local/imported")

CHAIN = ["nationality", "health_region", "local_or_imported"]
TOP_NATIONALITIES = 10  # collapse the long tail so the diagram stays readable

if set(CHAIN) <= set(fdf.columns) and not fdf.empty:
    flow = fdf[CHAIN].copy()
    for col in CHAIN:
        flow[col] = (flow[col].fillna("Unknown").astype(str)
                     .str.strip().replace("", "Unknown"))
    # Keep the top nationalities; bucket the rest as "Other".
    top = flow["nationality"].value_counts().head(TOP_NATIONALITIES).index
    flow["nationality"] = flow["nationality"].where(
        flow["nationality"].isin(top), "Other")

    # One distinct colour per health region; each region's incoming
    # (nationality→region) and outgoing (region→local/imported) bands share it.
    regions = list(flow["health_region"].drop_duplicates().sort_values())
    region_color = {r: who.CATEGORICAL[i % len(who.CATEGORICAL)]
                    for i, r in enumerate(regions)}

    def _rgba(hex_color: str, alpha: float) -> str:
        h = hex_color.lstrip("#")
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
        return f"rgba({r},{g},{b},{alpha})"

    # Build a node index per layer so identical labels in different layers
    # (e.g. a region that shares a name with a nationality) stay distinct.
    # Nationality and region labels are bolded (local/imported left plain).
    labels: list[str] = []
    node_id: dict[tuple[int, str], int] = {}
    for layer, col in enumerate(CHAIN):
        for val in flow[col].drop_duplicates().sort_values():
            node_id[(layer, val)] = len(labels)
            labels.append(f"<b>{val}</b>" if layer < 2 else val)

    def _node_color(layer: int, val: str) -> str:
        if layer == 0:
            return who.WHO_BLUE
        if layer == 1:
            return region_color[val]
        return {"Local": who.WHO_GREEN, "Imported": who.WHO_AMBER}.get(
            val, who.WHO_GREY)

    node_colors = [_node_color(layer, val) for (layer, val) in node_id]

    src, tgt, val, link_colors = [], [], [], []
    for layer in range(len(CHAIN) - 1):
        c_src, c_tgt = CHAIN[layer], CHAIN[layer + 1]
        grp = flow.groupby([c_src, c_tgt]).size().reset_index(name="n")
        for _, row in grp.iterrows():
            src.append(node_id[(layer, row[c_src])])
            tgt.append(node_id[(layer + 1, row[c_tgt])])
            val.append(int(row["n"]))
            # Colour the band by the region it touches (target on the way in,
            # source on the way out) so each region's flow is traceable.
            region = row[c_tgt] if layer == 0 else row[c_src]
            link_colors.append(_rgba(region_color[region], 0.45))

    sankey = go.Figure(go.Sankey(
        arrangement="snap",
        textfont=dict(color="black", size=13),
        node=dict(label=labels, color=node_colors, pad=16, thickness=16,
                  line=dict(color="white", width=0.5)),
        link=dict(source=src, target=tgt, value=val, color=link_colors),
    ))
    st.plotly_chart(who.style_fig(sankey, height=520), use_container_width=True)
    st.caption(
        f"Flow of {len(flow):,} filtered cases from nationality through health "
        f"region to local/imported classification. Nationalities beyond the top "
        f"{TOP_NATIONALITIES} are grouped as “Other”; missing values shown as "
        f"“Unknown”.")
else:
    st.info("Transmission chain needs the nationality, health_region and "
            "local_or_imported columns — not available for the current filter.")
