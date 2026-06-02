"""Data Quality: latest Great Expectations validation run, rejects, unmapped values."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from chikungunya_pipeline.config import get_settings  # noqa: E402
from chikungunya_pipeline.pipeline import default_source, run_pipeline  # noqa: E402
from theme import who_style as who  # noqa: E402
from data_access import load_cases  # noqa: E402

st.set_page_config(page_title="Data Quality", page_icon="✅", layout="wide")
who.apply_theme()
who.header("Data Quality", "Run ingestion, review the latest validation run and rejected rows")

settings = get_settings()
rejects_dir = settings.resolve(settings.rejects_dir)

# --- Manual ingestion trigger ---------------------------------------------
st.subheader("Run data ingestion")
src = default_source()
st.caption(f"Source workbook: `{src}`" if src else "No source workbook configured.")
col_a, col_b, _ = st.columns([1, 1, 2])
dry = col_a.button("Validate only (dry-run)", use_container_width=True)
live = col_b.button("Ingest & load to DB", type="primary", use_container_width=True)

if dry or live:
    with st.status("Running pipeline …", expanded=True) as status:
        try:
            res = run_pipeline(dry_run=dry, log=lambda m: st.write(m))
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
                st.caption(f"Skipped duplicates: {res.skipped_duplicate}"
                           + (f" · archived → {res.archived_to}" if res.archived_to else ""))
                load_cases.clear()  # refresh dashboard data on next view

st.divider()


def _latest(glob: str) -> Path | None:
    files = sorted(rejects_dir.glob(glob), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


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

st.subheader("Rejected rows")
rej = _latest("rejects_*.csv")
if rej is not None:
    rdf = pd.read_csv(rej)
    st.caption(f"{len(rdf)} rejected row(s) · {rej.name}")
    st.dataframe(rdf, use_container_width=True, hide_index=True)
    st.download_button("Download rejects CSV", rdf.to_csv(index=False), file_name=rej.name)
else:
    st.success("No rejected rows in the latest run.")

st.subheader("Unmapped reference values (need review)")
unmapped_files = sorted(rejects_dir.glob("unmapped_*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
if unmapped_files:
    for f in unmapped_files[:6]:
        with st.expander(f.name):
            st.dataframe(pd.read_csv(f), use_container_width=True, hide_index=True)
else:
    st.success("No unmapped values logged.")
