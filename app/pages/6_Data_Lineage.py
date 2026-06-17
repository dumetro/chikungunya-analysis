"""Data Lineage: report of transformations applied by the pipeline.

Reads the append-only pipeline_transformations audit table: SN-keyed corrections
and reference/lookup normalisations (raw -> canonical).
"""

from __future__ import annotations

import plotly.express as px
import streamlit as st

from data_access import load_transformations
from theme import who_style as who

st.set_page_config(page_title="Data Lineage", page_icon="🧬", layout="wide")
who.apply_theme()
who.top_nav(active="Data Lineage")
who.header("Data Lineage", "Transformations applied to source rows (corrections & normalization)",
           eyebrow="Provenance")

tx = load_transformations()
if tx.empty:
    st.info("No transformations recorded yet. Run the pipeline to populate the lineage log.")
    st.stop()

with st.container(key="lineage_content"):
    # Optional run filter.
    runs = ["All runs"] + sorted(tx["run_id"].dropna().unique().tolist(), reverse=True)
    chosen = st.selectbox("Run", runs)
    view = tx if chosen == "All runs" else tx[tx["run_id"] == chosen]

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Transformations", f"{len(view):,}")
    k2.metric("Rows affected", f"{view['sn'].nunique():,}")
    k3.metric("Columns affected", f"{view['column_name'].nunique():,}")
    k4.metric("Corrections", f"{int((view['stage'] == 'correction').sum()):,}")

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        who.section("By column", "What changed")
        by_col = view["column_name"].fillna("—").value_counts().head(15).reset_index()
        by_col.columns = ["column", "count"]
        fig = px.bar(by_col, x="count", y="column", orientation="h")
        fig.update_traces(marker_color=who.WHO_BLUE)
        fig.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(who.style_fig(fig), use_container_width=True)
    with c2:
        who.section("By action", "How it changed")
        by_act = view["action"].value_counts().reset_index()
        by_act.columns = ["action", "count"]
        fig = px.bar(by_act, x="action", y="count", color="action")
        fig.update_layout(showlegend=False)
        st.plotly_chart(who.style_fig(fig), use_container_width=True)

    st.divider()
    who.section("Trace a case by SN", "Per-row lineage")
    sn = st.text_input("Source SN")
    if sn:
        trace = view[view["sn"].astype(str) == sn.strip()]
        if trace.empty:
            st.warning(f"No transformations recorded for SN {sn}.")
        else:
            st.dataframe(
                trace[["stage", "column_name", "action", "old_value", "new_value", "applied_at"]],
                use_container_width=True, hide_index=True,
            )

    st.divider()
    who.section("All transformations", "Audit log")
    st.dataframe(view, use_container_width=True, hide_index=True)
    st.download_button("Download lineage CSV", view.to_csv(index=False),
                       file_name="data_lineage.csv")
