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
> `occupations`, `analysis_lookups`) and the `*_raw_map` tables. DDL lives in
> [`db_scripts/`](db_scripts/).

## Pipeline stages

| Stage | Module | What it does |
|-------|--------|--------------|
| Ingest | `ingest.py` | Reads the Excel sheet, maps headers → DB columns via `config/column_mapping.yaml`, keeps `_source_row` for traceability. |
| Sanitize | `sanitize.py` | Trims/cases strings, canonical Yes/No & gender, numeric coercion, **all dates → ISO 8601** via `dates.to_iso8601()`. |
| Normalize | `normalize.py` | Maps `occupation`/`nationality`/`symptoms`/`comorbidities_pmh` to canonical reference values via the `*_raw_map` + reference tables. Unmapped values are logged with fuzzy suggestions — never dropped. |
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
  column lists, coded & multivalue column entities, per-value overrides.
  *Edit this when the spreadsheet layout changes — no code change needed.*
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
  with `rapidfuzz` suggestions. Extend the `*_raw_map` tables, then re-run.
- `data/archive/` — successfully processed source files.

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
