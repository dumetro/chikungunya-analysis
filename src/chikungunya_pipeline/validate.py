"""Stage 4 — validate the cleaned DataFrame with the Great Expectations core.

Uses an *ephemeral* GX context (no project boilerplate) so the suite runs
anywhere. Column-level rules (ranges, allowed sets, date ordering) are expressed
as GX expectations; two conditional rules that mirror DB CHECK constraints are
enforced in pandas because they are awkward to express element-wise.

The result splits the input into ``passed`` (safe to load) and ``failed`` rows,
with a human-readable reason per failed row for the rejects file and the Data
Quality dashboard page.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

import great_expectations as gx
import great_expectations.expectations as gxe

from .config import get_settings

_RESULT_FORMAT = {
    "result_format": "COMPLETE",
    "unexpected_index_column_names": ["_source_row"],
}


@dataclass
class ValidationOutcome:
    passed: pd.DataFrame
    failed: pd.DataFrame  # includes a 'reject_reasons' column
    summary: dict[str, Any] = field(default_factory=dict)

    @property
    def n_passed(self) -> int:
        return len(self.passed)

    @property
    def n_failed(self) -> int:
        return len(self.failed)


def load_expectations_config(path: Path | None = None) -> dict:
    settings = get_settings()
    path = settings.resolve(path or settings.expectations_path)
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _build_suite(cfg: dict, columns: set[str]) -> gx.ExpectationSuite:
    suite = gx.ExpectationSuite(name="chikungunya_analysis")

    for col, rng in (cfg.get("ranges") or {}).items():
        if col in columns:
            suite.add_expectation(
                gxe.ExpectColumnValuesToBeBetween(
                    column=col, min_value=rng.get("min"), max_value=rng.get("max")
                )
            )

    for col, allowed in (cfg.get("allowed_sets") or {}).items():
        if col in columns:
            # Coerce to str so YAML's bool-ish tokens (yes/no/on/off) compare to
            # the canonical string cell values rather than to True/False.
            value_set = [str(v) for v in allowed]
            suite.add_expectation(
                gxe.ExpectColumnValuesToBeInSet(column=col, value_set=value_set)
            )

    for pair in cfg.get("date_order") or []:
        later, earlier = pair.get("later"), pair.get("earlier")
        if later in columns and earlier in columns:
            suite.add_expectation(
                gxe.ExpectColumnPairValuesAToBeGreaterThanB(
                    column_A=later,
                    column_B=earlier,
                    or_equal=True,
                    ignore_row_if="either_value_is_missing",
                )
            )
    return suite


def _collect_unexpected(result_dict: dict) -> tuple[set, str]:
    """Return (failed _source_row set, expectation label) from one result."""
    cfg = result_dict.get("expectation_config", {})
    kwargs = cfg.get("kwargs", {})
    label = cfg.get("type", "expectation")
    target = kwargs.get("column") or f"{kwargs.get('column_A')}>={kwargs.get('column_B')}"
    res = result_dict.get("result", {})
    rows: set = set()
    for item in res.get("unexpected_index_list") or []:
        if isinstance(item, dict):
            if "_source_row" in item:
                rows.add(item["_source_row"])
        else:
            rows.add(item)
    return rows, f"{label}[{target}]"


def _conditional_rejects(df: pd.DataFrame) -> dict[Any, list[str]]:
    """Pandas checks mirroring DB CHECK constraints. Keyed by _source_row."""
    reasons: dict[Any, list[str]] = {}

    def flag(mask: pd.Series, reason: str):
        for sr in df.loc[mask, "_source_row"]:
            reasons.setdefault(sr, []).append(reason)

    if {"gestation_week", "pregnancy"} <= set(df.columns):
        bad = df["gestation_week"].notna() & (df["pregnancy"] != "Yes")
        flag(bad, "gestation_week set but pregnancy != Yes")

    if {"if_admitted", "date_of_admission"} <= set(df.columns):
        bad = (df["if_admitted"] == "Yes") & df["date_of_admission"].isna()
        flag(bad, "admitted=Yes but date_of_admission missing")

    return reasons


def validate_dataframe(df: pd.DataFrame, cfg: dict | None = None) -> ValidationOutcome:
    """Validate df; return passed/failed split with reasons."""
    cfg = cfg or load_expectations_config()
    columns = set(df.columns)

    # --- GX column-level validation (ephemeral context) ---
    context = gx.get_context(mode="ephemeral")
    try:  # silence tqdm metric-calculation progress bars
        from great_expectations.data_context.types.base import ProgressBarsConfig

        context.variables.progress_bars = ProgressBarsConfig(
            globally=False, metric_calculations=False
        )
    except Exception:
        pass
    data_source = context.data_sources.add_pandas("pandas_runtime")
    asset = data_source.add_dataframe_asset(name="cases")
    batch_def = asset.add_batch_definition_whole_dataframe("batch")
    suite = _build_suite(cfg, columns)

    batch = batch_def.get_batch(batch_parameters={"dataframe": df})
    gx_result = batch.validate(suite, result_format=_RESULT_FORMAT)

    reasons: dict[Any, list[str]] = {}
    expectation_summaries = []
    for r in gx_result.results:
        rd = r.to_json_dict() if hasattr(r, "to_json_dict") else dict(r)
        success = rd.get("success", True)
        bad_rows, label = _collect_unexpected(rd)
        expectation_summaries.append(
            {"expectation": label, "success": success, "n_unexpected": len(bad_rows)}
        )
        for sr in bad_rows:
            reasons.setdefault(sr, []).append(label)

    # --- Conditional pandas checks ---
    if cfg.get("conditional_rules", True):
        for sr, why in _conditional_rejects(df).items():
            reasons.setdefault(sr, []).extend(why)

    failed_rows = set(reasons)
    failed_mask = df["_source_row"].isin(failed_rows)
    failed = df.loc[failed_mask].copy()
    failed["reject_reasons"] = failed["_source_row"].map(
        lambda sr: "; ".join(reasons.get(sr, []))
    )
    passed = df.loc[~failed_mask].copy()

    summary = {
        "n_input": len(df),
        "n_passed": len(passed),
        "n_failed": len(failed),
        "overall_success": bool(gx_result.success) and not failed_rows,
        "expectations": expectation_summaries,
    }
    return ValidationOutcome(passed=passed, failed=failed, summary=summary)
