"""End-to-end pipeline orchestrator with a Typer CLI.

    python -m chikungunya_pipeline.pipeline run --file data/incoming/cases.xlsx
    python -m chikungunya_pipeline.pipeline run --file ... --dry-run
    python -m chikungunya_pipeline.pipeline run            # newest file in INCOMING_DIR

Stages: ingest -> sanitize -> normalize -> validate (GX) -> load.
With --dry-run nothing is written to the database; per-stage counts and the
validation summary are printed and reject/unmapped artefacts are still written.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer

from .config import get_settings
from .ingest import read_excel
from .mapping_config import load_mapping
from .normalize import normalize_dataframe
from .sanitize import sanitize_dataframe
from .validate import load_expectations_config, validate_dataframe

app = typer.Typer(add_completion=False, help="Chikungunya data-cleaning pipeline.")


def _echo(msg: str) -> None:
    typer.echo(msg)


def _newest_incoming(settings) -> Optional[Path]:
    incoming = settings.resolve(settings.incoming_dir)
    files = sorted(
        [p for p in incoming.glob("*.xls*")], key=lambda p: p.stat().st_mtime, reverse=True
    )
    return files[0] if files else None


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


@app.command()
def run(
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="Excel file to process."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Do not write to the database."),
    mode: Optional[str] = typer.Option(None, "--mode", help="append | replace (default from .env)."),
):
    """Run the full pipeline on one Excel file."""
    settings = get_settings()
    mode = mode or settings.load_mode
    rejects_dir = settings.resolve(settings.rejects_dir)
    rejects_dir.mkdir(parents=True, exist_ok=True)

    src = file or _newest_incoming(settings)
    if src is None:
        raise typer.BadParameter("No file given and none found in INCOMING_DIR.")
    src = Path(src)
    _echo(f"[1/5] Ingesting {src} ...")
    mapping = load_mapping()
    ingested = read_excel(src, mapping)
    _echo(f"      rows={len(ingested.df)}  mapped={len(ingested.mapped_headers)}  "
          f"unmapped={ingested.unmapped_headers or '-'}")

    _echo("[2/5] Sanitising ...")
    clean = sanitize_dataframe(ingested.df, mapping)

    _echo("[3/5] Normalising against reference tables ...")
    try:
        normalized, unmapped = normalize_dataframe(
            clean, mapping.coded_columns, mapping.multivalue_columns
        )
        if unmapped.rows:
            stamp = _timestamp()
            for col, grp in unmapped.to_frame().groupby("column"):
                out = rejects_dir / f"unmapped_{col}_{stamp}.csv"
                grp.drop_duplicates("raw_value").to_csv(out, index=False)
            _echo(f"      logged {len(unmapped.rows)} unmapped value(s) for review -> {rejects_dir}")
    except Exception as exc:  # DB unavailable in --dry-run without DB, etc.
        if not dry_run:
            raise
        _echo(f"      [skip] normalization needs DB ({exc.__class__.__name__}); continuing dry-run")
        normalized = clean

    _echo("[4/5] Validating (Great Expectations) ...")
    cfg = load_expectations_config()
    outcome = validate_dataframe(normalized, cfg)
    _echo(f"      passed={outcome.n_passed}  failed={outcome.n_failed}  "
          f"overall_success={outcome.summary['overall_success']}")

    stamp = _timestamp()
    # Persist validation summary for the Data Quality dashboard page.
    (rejects_dir / f"validation_summary_{stamp}.json").write_text(
        json.dumps({"file": str(src), **outcome.summary}, indent=2)
    )
    if outcome.n_failed:
        rej = rejects_dir / f"rejects_{src.stem}_{stamp}.csv"
        outcome.failed.to_csv(rej, index=False)
        _echo(f"      rejects written -> {rej}")

    if dry_run:
        _echo("[5/5] Dry-run: skipping database load.")
        _echo(json.dumps(outcome.summary, indent=2))
        raise typer.Exit(0)

    _echo(f"[5/5] Loading {outcome.n_passed} row(s) into chikungunya_analysis (mode={mode}) ...")
    from .load import load_dataframe  # imported here so dry-run needs no DB driver

    to_load = outcome.passed.drop(columns=["reject_reasons"], errors="ignore")
    result = load_dataframe(to_load, source_file=src.name, mode=mode)
    _echo(f"      inserted={result.n_inserted}  skipped_duplicate={result.n_skipped_duplicate}")

    # Archive the processed file.
    archive = settings.resolve(settings.archive_dir)
    archive.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(archive / f"{src.stem}_{stamp}{src.suffix}"))
    _echo(f"      archived source -> {archive}")


@app.command()
def check_db():
    """Verify the database connection."""
    from .db import ping

    typer.echo("Database reachable." if ping() else "Database NOT reachable.")


if __name__ == "__main__":
    app()
