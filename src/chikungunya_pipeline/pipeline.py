"""End-to-end pipeline orchestrator with a reusable core + Typer CLI.

Ingestion is always triggered manually — by the CLI:

    python -m chikungunya_pipeline.pipeline run                 # default source file
    python -m chikungunya_pipeline.pipeline run --dry-run
    python -m chikungunya_pipeline.pipeline run --file other.xlsx

or by the "Run ingestion" button on the Streamlit dashboard, which calls
:func:`run_pipeline` directly.

Stages: ingest -> sanitize -> normalize -> validate (GX) -> load.
With ``dry_run`` nothing is written to the database; per-stage counts and the
validation summary are produced and reject/unmapped artefacts are still written.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

import typer

from .config import get_settings
from .ingest import read_excel
from .mapping_config import load_mapping
from .normalize import normalize_dataframe
from .sanitize import sanitize_dataframe
from .validate import load_expectations_config, validate_dataframe

app = typer.Typer(add_completion=False, help="Chikungunya data-cleaning pipeline.")


@dataclass
class PipelineRunResult:
    source: str
    dry_run: bool
    ingested_rows: int = 0
    unmapped_headers: list[str] = field(default_factory=list)
    passed: int = 0
    failed: int = 0
    overall_success: bool = False
    inserted: int = 0
    skipped_duplicate: int = 0
    load_failed: int = 0
    archived_to: Optional[str] = None
    summary: dict = field(default_factory=dict)
    messages: list[str] = field(default_factory=list)


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def default_source() -> Optional[Path]:
    """The configured source workbook, else the newest file in INCOMING_DIR."""
    settings = get_settings()
    configured = settings.resolve(settings.source_file)
    if configured.exists():
        return configured
    incoming = settings.resolve(settings.incoming_dir)
    files = sorted(incoming.glob("*.xls*"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def run_pipeline(
    file: Optional[Path | str] = None,
    *,
    dry_run: bool = False,
    mode: Optional[str] = None,
    log: Callable[[str], None] = print,
) -> PipelineRunResult:
    """Run the full pipeline on one Excel file. Reusable by CLI and dashboard."""
    settings = get_settings()
    mode = mode or settings.load_mode
    rejects_dir = settings.resolve(settings.rejects_dir)
    rejects_dir.mkdir(parents=True, exist_ok=True)

    src = Path(file) if file else default_source()
    if src is None or not Path(src).exists():
        raise FileNotFoundError(
            f"Source file not found: {src or '(none configured)'}. "
            "Set SOURCE_FILE in .env or pass an explicit file."
        )
    src = Path(src)

    result = PipelineRunResult(source=str(src), dry_run=dry_run)

    def emit(msg: str) -> None:
        result.messages.append(msg)
        log(msg)

    emit(f"[1/5] Ingesting {src} ...")
    mapping = load_mapping()
    ingested = read_excel(src, mapping)
    result.ingested_rows = len(ingested.df)
    result.unmapped_headers = ingested.unmapped_headers
    emit(f"      rows={result.ingested_rows}  mapped={len(ingested.mapped_headers)}")

    emit("[2/5] Sanitising ...")
    clean = sanitize_dataframe(ingested.df, mapping)

    emit("[3/5] Normalising against reference + lookup tables ...")
    from .normalize import load_lookup_sets

    lookup_sets = load_lookup_sets()  # DB, or seed-CSV fallback when offline
    allowed_sets = {col: lookup_sets.allowed(cat)
                    for col, cat in mapping.lookup_columns.items()
                    if lookup_sets.allowed(cat)}
    try:
        normalized, unmapped = normalize_dataframe(
            clean,
            mapping.coded_columns,
            mapping.multivalue_columns,
            lookup_columns=mapping.lookup_columns,
            value_overrides=mapping.value_overrides,
            value_patterns=mapping.value_patterns,
            lookup_sets=lookup_sets,
        )
        if unmapped.rows:
            stamp = _timestamp()
            for col, grp in unmapped.to_frame().groupby("column"):
                out = rejects_dir / f"unmapped_{col}_{stamp}.csv"
                grp.drop_duplicates("raw_value").to_csv(out, index=False)
            emit(f"      logged {len(unmapped.rows)} unmapped value(s) for review -> {rejects_dir}")
    except Exception as exc:
        if not dry_run:
            raise
        emit(f"      [skip] reference normalization needs DB ({exc.__class__.__name__}); "
             "applying lookup normalization only")
        normalized, unmapped = normalize_dataframe(
            clean, {}, {},
            lookup_columns=mapping.lookup_columns,
            value_overrides=mapping.value_overrides,
            value_patterns=mapping.value_patterns,
            lookup_sets=lookup_sets,
        )

    # Derive the WHO/PAHO case classification from the normalised columns so it
    # is validated and persisted alongside the case.
    try:
        from .classify import classify_cases

        normalized["case_classification"] = classify_cases(normalized)
        emit("      derived case_classification "
             f"({normalized['case_classification'].value_counts().to_dict()})")
    except Exception as exc:
        emit(f"      [skip] case classification ({exc.__class__.__name__})")

    emit("[4/5] Validating (Great Expectations) ...")
    cfg = load_expectations_config()
    # Introspect the target table so we can validate source values against the
    # real schema (type / nullability / varchar length / int range) and reject
    # mismatches before they raise a DB error on load.
    try:
        from .load import target_schema

        schema = target_schema()
    except Exception:
        schema = {}
    outcome = validate_dataframe(normalized, cfg, allowed_sets=allowed_sets, schema=schema)
    result.passed = outcome.n_passed
    result.failed = outcome.n_failed
    result.overall_success = bool(outcome.summary.get("overall_success"))
    result.summary = outcome.summary
    emit(f"      passed={outcome.n_passed}  failed={outcome.n_failed}  "
         f"overall_success={result.overall_success}")

    stamp = _timestamp()
    (rejects_dir / f"validation_summary_{stamp}.json").write_text(
        json.dumps({"file": str(src), **outcome.summary}, indent=2)
    )
    if outcome.n_failed:
        rej = rejects_dir / f"rejects_{src.stem}_{stamp}.csv"
        outcome.failed.to_csv(rej, index=False)
        emit(f"      rejects written -> {rej}")

    if dry_run:
        emit("[5/5] Dry-run: skipping database load.")
        return result

    emit(f"[5/5] Loading {outcome.n_passed} row(s) into chikungunya_analysis (mode={mode}) ...")
    from .load import load_dataframe  # imported here so dry-run needs no DB driver

    to_load = outcome.passed.drop(columns=["reject_reasons"], errors="ignore")
    load_result = load_dataframe(to_load, source_file=src.name, mode=mode)
    result.inserted = load_result.n_inserted
    result.skipped_duplicate = load_result.n_skipped_duplicate
    result.load_failed = load_result.n_failed
    emit(f"      inserted={load_result.n_inserted}  "
         f"skipped_duplicate={load_result.n_skipped_duplicate}  failed={load_result.n_failed}")

    # Any rows the DB rejected (despite validation) are quarantined, not lost.
    if load_result.n_failed and load_result.failures is not None:
        err_path = rejects_dir / f"load_errors_{src.stem}_{stamp}.csv"
        load_result.failures.to_csv(err_path, index=False)
        emit(f"      {load_result.n_failed} row(s) rejected by DB -> {err_path}")

    # Archive the processed file.
    archive = settings.resolve(settings.archive_dir)
    archive.mkdir(parents=True, exist_ok=True)
    dest = archive / f"{src.stem}_{stamp}{src.suffix}"
    shutil.move(str(src), str(dest))
    result.archived_to = str(dest)
    emit(f"      archived source -> {dest}")
    return result


@app.command()
def run(
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="Excel file (default: SOURCE_FILE)."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Do not write to the database."),
    mode: Optional[str] = typer.Option(None, "--mode", help="append | replace (default from .env)."),
):
    """Run the full pipeline on one Excel file."""
    try:
        result = run_pipeline(file, dry_run=dry_run, mode=mode, log=typer.echo)
    except FileNotFoundError as exc:
        raise typer.BadParameter(str(exc))
    if dry_run:
        typer.echo(json.dumps(result.summary, indent=2))


@app.command()
def check_db():
    """Verify the database connection."""
    from .db import ping

    typer.echo("Database reachable." if ping() else "Database NOT reachable.")


if __name__ == "__main__":
    app()
