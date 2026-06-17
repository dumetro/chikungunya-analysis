"""Data Quality: latest Great Expectations validation run, rejects, unmapped values."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from chikungunya_pipeline.config import get_settings  # noqa: E402
from chikungunya_pipeline.mapping_config import source_headers  # noqa: E402
from chikungunya_pipeline.pipeline import default_source, run_pipeline  # noqa: E402
from theme import who_style as who  # noqa: E402
from data_access import load_cases  # noqa: E402

st.set_page_config(page_title="Data Quality", page_icon="✅", layout="wide")
who.apply_theme()
who.top_nav(active="Data Quality")
who.header("Data Quality", "Run ingestion, review the latest validation run and rejected rows",
           eyebrow="Pipeline")

settings = get_settings()
rejects_dir = settings.resolve(settings.rejects_dir)

def _latest(glob: str) -> "Path | None":
    files = sorted(rejects_dir.glob(glob), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


@st.cache_data(ttl=300, show_spinner=False)
def _csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


@st.cache_data(ttl=300, show_spinner=False)
def _xlsx_bytes(df: pd.DataFrame) -> bytes:
    out = df.copy()
    # Excel can't store timezone-aware datetimes (e.g. created_at/updated_at).
    for col in out.select_dtypes(include=["datetimetz"]).columns:
        out[col] = out[col].dt.tz_localize(None)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xl:
        out.to_excel(xl, index=False, sheet_name="cases")
    return buf.getvalue()


_REASON_COLS = ["failed_columns", "reject_reasons"]


def _rejects_source_xlsx(rdf: pd.DataFrame) -> bytes:
    """Reshape the rejects table back into the source spreadsheet layout (original
    headers) so it can be corrected and re-imported. Keeps the reason columns at
    the end so the file can be filtered by rejection reason."""
    headers = source_headers()  # db col -> original source header (mapping order)
    out = rdf.copy()
    if "_sn" in out.columns:
        out["SN"] = out["_sn"]  # restore the source identifier
    src_cols = [db for db in headers if db in out.columns]
    ordered = (["SN"] if "SN" in out.columns else []) + src_cols \
        + [c for c in _REASON_COLS if c in out.columns]
    return _xlsx_bytes(out[ordered].rename(columns=headers))


@st.dialog("Upload a data file")
def _upload_dialog():
    incoming = settings.resolve(settings.incoming_dir)
    st.write(f"The file is saved to `{incoming}` and queued for cleaning & validation.")
    up = st.file_uploader("Excel workbook", type=["xlsx", "xls"])
    if up is not None:
        st.caption(f"**{up.name}** · {up.size / 1024:,.0f} KB")
        dest = incoming / up.name
        if dest.exists():
            st.warning("A file with this name already exists and will be overwritten.")
        if st.button("Save & set as source", type="primary", use_container_width=True):
            incoming.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(up.getbuffer())
            st.session_state["uploaded_source"] = str(dest)
            st.success(f"Saved → {dest}")
            st.rerun()


# --- Manual ingestion trigger ---------------------------------------------
st.subheader("Run data ingestion")
# Active source: an uploaded file (this session) takes precedence over the default.
_default = default_source()
src = st.session_state.get("uploaded_source") or (str(_default) if _default else None)
st.caption(f"Source workbook: `{src}`" if src else "No source workbook configured — upload one.")

up_col, _ = st.columns([1, 3])
if up_col.button("📤 Upload data file", use_container_width=True):
    _upload_dialog()

# Centre the two action buttons using spacer columns.
_, col_a, col_b, _ = st.columns([1, 1.5, 1.5, 1])
dry = col_a.button("Validate only (dry-run)", use_container_width=True, disabled=not src)
live = col_b.button("Ingest & load to DB", type="primary", use_container_width=True, disabled=not src)

if dry or live:
    with st.status("Running pipeline …", expanded=True) as status:
        try:
            res = run_pipeline(file=src, dry_run=dry, log=lambda m: st.write(m))
        except Exception as exc:
            status.update(label="Pipeline failed", state="error")
            st.error(str(exc))
        else:
            verb = "Dry-run complete" if dry else "Ingestion complete"
            status.update(label=verb, state="complete")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Ingested", res.ingested_rows)
            m2.metric("Passed", res.passed)
            m3.metric("Failed", res.failed)
            m4.metric("Inserted" if not dry else "Would load",
                      res.inserted if not dry else res.passed)
            if not dry:
                st.caption(
                    f"Inserted: {res.inserted} · skipped duplicates: {res.skipped_duplicate} "
                    f"· DB-rejected: {res.load_failed}"
                    + (f" · archived → {res.archived_to}" if res.archived_to else "")
                )
                if res.load_failed:
                    st.warning(
                        f"{res.load_failed} row(s) were rejected by the database and "
                        "quarantined to a load_errors CSV (see Rejected rows below)."
                    )
                load_cases.clear()  # refresh dashboard data on next view
                # The processed file was archived out of incoming; drop the stale path.
                st.session_state.pop("uploaded_source", None)

st.divider()

# --- Download the cleaned dataset (current chikungunya_analysis contents) ---
st.subheader("Cleaned dataset")
try:
    clean_df = load_cases()
except Exception as exc:  # DB unreachable etc.
    clean_df = None
    st.caption(f"Cleaned data unavailable: {exc.__class__.__name__}")
if clean_df is not None and not clean_df.empty:
    st.caption(f"{len(clean_df):,} cleaned rows currently in chikungunya_analysis.")
    d1, d2, _ = st.columns([1.2, 1.2, 2])
    d1.download_button(
        "⬇️ Download CSV", _csv_bytes(clean_df),
        file_name="chikungunya_analysis_clean.csv", mime="text/csv",
        use_container_width=True,
    )
    d2.download_button(
        "⬇️ Download Excel", _xlsx_bytes(clean_df),
        file_name="chikungunya_analysis_clean.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
elif clean_df is not None:
    st.caption("No rows in chikungunya_analysis yet — load a file above.")

st.divider()

# --- Data completeness by category -----------------------------------------
st.subheader("Data completeness by category")
if clean_df is not None and not clean_df.empty:
    # Prioritised surveillance fields, critical first. Each maps to one or more
    # DB columns; completeness = mean share of non-blank values across them.
    COMPLETENESS_CATEGORIES = [
        ("Case counts (notification date)", ["date_of_notification"]),
        ("Epi week", ["epi_week"]),
        ("Geographic (region / locality)", ["health_region", "locality"]),
        ("Age & sex", ["age", "gender"]),
        ("Case classification", ["case_classification"]),
        ("Local vs imported", ["local_or_imported"]),
        ("Outcome", ["outcome"]),
        ("Disposition", ["dmu_hospitalised_tba_missing"]),
        ("Symptoms", ["symptoms"]),
        ("Onset date", ["date_of_onset_symptoms"]),
        ("Nationality", ["nationality"]),
        ("Occupation", ["occupation"]),
        ("Lab result (PCR)", ["pcr_result"]),
        ("Epi linkage", ["epi_linkage"]),
        ("Comorbidities", ["comorbidities_pmh"]),
    ]

    def _completeness(cols: list[str]) -> float:
        present = [c for c in cols if c in clean_df.columns]
        if not present:
            return 0.0
        shares = [(clean_df[c].notna() & (clean_df[c].astype(str).str.strip() != "")).mean()
                  for c in present]
        return round(sum(shares) / len(shares) * 100, 1)

    rows = [{"category": lbl, "pct": _completeness(cols)}
            for lbl, cols in COMPLETENESS_CATEGORIES]
    cdf = pd.DataFrame(rows)

    def _band_color(p: float) -> str:
        return who.WHO_GREEN if p >= 80 else (who.WHO_AMBER if p >= 50 else who.WHO_RED)

    cdf["color"] = cdf["pct"].map(_band_color)
    fig = px.bar(cdf, x="pct", y="category", orientation="h",
                 text=cdf["pct"].map(lambda v: f"{v:.0f}%"))
    fig.update_traces(marker_color=list(cdf["color"]), textposition="outside",
                      cliponaxis=False)
    fig.update_xaxes(range=[0, 108], ticksuffix="%", title="")
    fig.update_yaxes(categoryorder="array", categoryarray=list(cdf["category"])[::-1],
                     title="")
    st.plotly_chart(who.style_fig(fig, height=44 * len(cdf) + 80),
                    use_container_width=True)
    gaps = cdf.loc[cdf["pct"] < 50, "category"].tolist()
    st.caption(
        "Share of rows with a recorded (non-blank) value per surveillance field, "
        "ordered by priority. Green ≥80% · amber 50–79% · red <50%."
        + (f" **Critical gaps (<50%):** {', '.join(gaps)}." if gaps else ""))
    who.notes(
        "Field-level data completeness for the loaded dataset — which critical "
        "surveillance variables are well captured versus sparsely recorded.",
        "Measures non-blank values only, not correctness. Categories grouping "
        "several columns average their completeness. Recompute each load; as new "
        "data arrives the bars move, so use this to target the source fields that "
        "most need improvement (here: PCR result, epi-linkage and comorbidities).")
else:
    st.caption("Completeness chart needs loaded data.")

st.divider()

# Everything below the buttons sits in a margin-constrained container
# (.st-key-dq_content) so wide tables never overflow the viewport.
with st.container(key="dq_content"):
    summary_file = _latest("validation_summary_*.json")
    if summary_file is None:
        st.info("No validation runs found yet. Run the pipeline to populate this page.")
        st.stop()

    summary = json.loads(summary_file.read_text())
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rows in file", summary.get("n_input", 0))
    c2.metric("Passed", summary.get("n_passed", 0))
    c3.metric("Failed", summary.get("n_failed", 0))
    c4.metric("Overall", "PASS" if summary.get("overall_success") else "FAIL")
    st.caption(f"Source: {summary.get('file', '?')} · report: {summary_file.name}")

    st.subheader("Expectation results")
    exp = pd.DataFrame(summary.get("expectations", []))
    if not exp.empty:
        def _row_style(r):
            bg = "#E9F7E5" if r["success"] else "#FBE4E6"
            return [f"background-color: {bg}; color: #1F2937"] * len(r)
        st.dataframe(exp.style.apply(_row_style, axis=1), use_container_width=True, hide_index=True)

    st.subheader("Rejected rows (failed validation)")
    rej = _latest("rejects_*.csv")
    if rej is not None:
        rdf = pd.read_csv(rej)
        st.caption(f"{len(rdf)} rejected row(s) · {rej.name}")
        st.dataframe(rdf, use_container_width=True, hide_index=True)
        st.download_button(
            "Download rejects to fix (.xlsx)",
            _rejects_source_xlsx(rdf),
            file_name=f"{rej.stem}_to_fix.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        st.caption(
            "Source-format workbook: original spreadsheet headers, plus "
            "`failed_columns` / `reject_reasons` at the end for filtering. Fix the "
            "flagged cells, then drop it in `data/incoming/` and re-run — the two "
            "reason columns are ignored on import, and already-loaded clean rows "
            "are skipped (content-hash dedupe). Note: values are post-cleaning, so "
            "multi-value fields (e.g. symptoms) are already canonicalised.")
    else:
        st.success("No rejected rows in the latest run.")

    st.subheader("Rows rejected by the database (during load)")
    load_err = _latest("load_errors_*.csv")
    if load_err is not None:
        ldf = pd.read_csv(load_err)
        st.caption(f"{len(ldf)} DB-rejected row(s) · {load_err.name}")
        st.dataframe(ldf, use_container_width=True, hide_index=True)
        st.download_button("Download load errors CSV", ldf.to_csv(index=False),
                           file_name=load_err.name)
    else:
        st.success("No database load errors in the latest run.")

    st.subheader("Unmapped reference values (need review)")
    # Cleared and rewritten on every pipeline run, so this reflects the latest run only.
    unmapped_files = sorted(rejects_dir.glob("unmapped_*.csv"), key=lambda p: p.name)
    if unmapped_files:
        for f in unmapped_files:
            with st.expander(f.name):
                st.dataframe(pd.read_csv(f), use_container_width=True, hide_index=True)
    else:
        st.success("No unmapped values logged.")
