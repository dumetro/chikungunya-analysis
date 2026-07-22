# Chikungunya Outbreak — Data Pipeline & WHO-Styled Dashboard

A repeatable, auditable pipeline that ingests outbreak case data from Excel,
cleans and normalises it, validates it with **Great Expectations**, and loads it
into PostgreSQL — plus a **Streamlit dashboard** (WHO styling) for analysis.

```
Excel  →  ingest  →  sanitize  →  normalize  →  validate (GX)  →  load (Postgres)
                                                                        │
                                                          Streamlit dashboard
```

## Quick start

```bash
make install                 # create .venv and install deps (incl. editable package)
cp .env.example .env         # then edit DATABASE_URL
make check-db                # verify the DB connection

# Drop an .xlsx into data/incoming/ then:
make dry-run                 # ingest→sanitize→normalize→validate, NO DB write
make pipeline                # full run incl. DB load (newest file in data/incoming)
make pipeline FILE=data/incoming/cases.xlsx   # specific file

make app                     # launch the dashboard
make test                    # unit tests
```

> Requires an existing PostgreSQL database containing `chikungunya_analysis`,
> the reference tables (`symptoms`, `nationalities`, `comorbidities`,
> `occupations`, `healthfacilities`, `analysis_lookups`) and the `*_raw_map`
> tables. DDL lives in [`db_scripts/`](db_scripts/).

## Pipeline stages

| Stage | Module | What it does |
|-------|--------|--------------|
| Ingest | `ingest.py` | Reads the Excel sheet, maps headers → DB columns via `config/column_mapping.yaml`, keeps `_source_row` and the source `SN` (`_sn`) for traceability. |
| Correct | `lineage.py` | Applies SN-keyed corrections from `config/corrections.yaml` (move/clear/set) for cross-pollinated values (e.g. a symptom string in the `pregnancy` column). Each change is logged for lineage. |
| Sanitize | `sanitize.py` | Trims/cases strings, canonical Yes/No & gender, numeric coercion, **all dates → ISO 8601** via `dates.to_iso8601()`. |
| Normalize | `normalize.py` | Maps `occupation`/`nationality`/`symptoms`/`comorbidities_pmh` and the facility columns `health_institution_attended`/`health_institution` to canonical reference values via the `*_raw_map` + reference tables. **Lookup-coded columns** (`gender`, `age_group`, `pcr_result`, `outcome`, `local_or_imported`, `active_passive`) are normalised against `analysis_lookups` by: case-insensitive exact match → `value_overrides` synonyms → `value_patterns` regex → else kept raw and logged with fuzzy suggestions. Nothing is dropped silently. |
| Validate | `validate.py` | Great Expectations **core** suite mirroring the DB CHECK constraints (ranges, allowed sets, date ordering, conditional rules). Splits rows into passed / rejected. |
| Load | `load.py` | Transactional bulk insert; SHA-256 content-hash dedupe via `pipeline_load_log`; `append` or `replace` mode. |

### The dedicated date normaliser
All date columns route through a single function, `chikungunya_pipeline.dates.to_iso8601()`,
which handles Excel serials, `DD/MM/YYYY`, ISO strings, textual months and blanks,
returning a `datetime.date` (ISO `YYYY-MM-DD`) or `None`. Day-first by default
(`DATE_DAYFIRST` in `.env`).

## Configuration

- **`.env`** — `DATABASE_URL`, paths, `DATE_DAYFIRST`, `LOAD_MODE` (via `pydantic-settings`).
- **`config/column_mapping.yaml`** — Excel header → DB column, date/int/Yes-No
  column lists, coded & multivalue column entities, `lookup_columns` (column →
  `analysis_lookups` category), `value_overrides` (synonyms) and `value_patterns`
  (regex → canonical). *Edit this when the spreadsheet layout changes or when the
  unmapped-values report surfaces new variants — no code change needed.*
- **`analysis_lookups`** is the canonical value list per category. To recognise a
  new value, add it to the table (see `db_scripts/seed_analysis_lookups_extra.sql`)
  or extend `value_overrides` / `value_patterns`. Offline (no DB) the pipeline
  falls back to `data/incoming/analysis_lookups.csv`.
- **Reference entity tables** (`symptoms`, `comorbidities`, `occupations`,
  `nationalities`, `healthfacilities`) hold the canonical names. The
  `healthfacilities` table is the canonical Mauritius facility list (name, type,
  region); dirty source spellings map to it through `healthfacility_raw_map`.
  See `db_scripts/healthfacilities.sql`, `db_scripts/healthfacility_raw_map.sql`
  and the `seed_healthfacilit*` scripts; `docs/healthfacility_mapping_review.csv`
  lists every source spelling and the facility it maps to (blank = left for
  review, e.g. `YCCH`, health-office / fever-watch surveillance entries). `symptoms` also carries optional
  `category` / `description` metadata — see
  `db_scripts/extend_symptoms_cdc_who.sql`, which adds those columns, seeds the
  CDC/WHO chikungunya symptom set, and backfills clinical groupings
  (Primary / Secondary / Severe / Other). To teach the pipeline a new dirty
  value, add a `(raw_value, <entity>_id)` row to the matching `*_raw_map` table;
  a multi-symptom raw string gets **one row per symptom** it contains (see
  `db_scripts/seed_symptom_raw_map.sql`). Separators in raw strings are commas,
  slashes and the word `AND` — except slash pairs that are themselves canonical
  names (e.g. `Arthralgia / Joint Pain`, `Myalgia / Body Ache`). The
  `fn_map_symptom(raw, symptom_name)` and `fn_map_comorbidity(...)` helper
  functions insert these rows by canonical name, so you needn't look up ids.
- **`config/expectations.yaml`** — validation ranges, allowed value sets, date-ordering
  pairs. *Keep `Yes`/`No` quoted (unquoted they are YAML booleans).*

## Dashboard

`make app` (or `streamlit run app/Home.py`). Pages:
**Home** (KPIs, epi curve, local/imported) · **Epi Curve** · **Demographics**
(age-sex pyramid, nationality, occupation) · **Clinical** (symptoms, comorbidities,
PCR, outcomes) · **Geographic** (region/locality, local vs imported) ·
**Data Quality** (latest GX run, rejects, unmapped values).

## Outputs & review

- `data/rejects/validation_summary_*.json` — per-run GX summary (feeds Data Quality page).
- `data/rejects/rejects_*.csv` — rows that failed validation, with reasons.
- `data/rejects/unmapped_<col>_*.csv` — source values not in the reference maps,
  with single-best `rapidfuzz` suggestions (a triage hint, not a decomposition —
  for a multi-symptom cell it only names the nearest canonical value). Add the
  verified `*_raw_map` rows (e.g. via `db_scripts/seed_symptom_raw_map.sql` or the
  `fn_map_*` helpers), then re-run.
- `data/archive/` — successfully processed source files.
- `data/rejects/transformations_*.csv` — per-run data-lineage events.

## Data lineage

Every correction and reference/lookup normalisation (raw → canonical) is recorded
as an append-only event in the **`pipeline_transformations`** audit table
(`db_scripts/pipeline_transformations.sql`; the pipeline also ensures it at load
time), keyed by source `SN`: `(run_id, sn, source_row, stage, column_name, action,
old_value, new_value, applied_at)`. The **Data Lineage** dashboard page reports it
(by column, by action, per-SN trace, CSV export). Edit `config/corrections.yaml`
to add SN-keyed fixes; whitespace/case cleanups (the sanitise stage) are not logged.

## Project layout

```
src/chikungunya_pipeline/   pipeline package (config, db, dates, ingest, sanitize,
                            normalize, validate, load, pipeline CLI)
app/                        Streamlit app (Home + pages/) and WHO theme
config/                     column_mapping.yaml, expectations.yaml
db_scripts/                 existing database DDL
tests/                      pytest unit tests
data/{incoming,rejects,archive}/
```

## Notes
- `normalize.py` introspects the reference tables at runtime (it auto-detects the
  `<entity>_id` and name columns), so it tolerates the exact DDL. If a reference
  table uses an unusual name column, adjust `_NAME_CANDIDATES` in `normalize.py`.
- Allowed-set values in `config/expectations.yaml` (e.g. `pcr_result`, `outcome`,
  `active_passive`) should match the canonical labels in `analysis_lookups`.
