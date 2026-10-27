-- Build the full chikungunya schema and seed the reference tables, in
-- dependency order. Every script is idempotent, so re-running is safe.
--
--   createdb -h localhost -U postgres chikungunya
--   psql -h localhost -U postgres -d chikungunya -f db_scripts/setup_all.sql

\set ON_ERROR_STOP on

-- Reference tables
\ir analysis_lookups.sql
\ir symptoms.sql
\ir comorbidities.sql
\ir occupations.sql
\ir nationalities.sql
\ir healthfacilities.sql

-- Raw -> canonical maps (FK to the reference tables) and helper functions
\ir symptom_raw_map.sql
\ir comorbidity_raw_map.sql
\ir occupation_raw_map.sql
\ir healthfacility_raw_map.sql
\ir fn_map_symptom.sql
\ir fn_map_comorbidity.sql

-- Case table and pipeline audit table
\ir chikungunya_analysis.sql
\ir add_case_classification.sql
\ir pipeline_transformations.sql

-- Seeds. seed_symptoms.sql pins the symptom_ids that seed_symptom_raw_map.sql
-- hard-codes, so it must run before extend_symptoms_cdc_who.sql inserts
-- further symptoms through the sequence.
\ir seed_analysis_lookups.sql
\ir seed_analysis_lookups_extra.sql
\ir seed_symptoms.sql
\ir extend_symptoms_cdc_who.sql
\ir seed_symptom_raw_map.sql
\ir seed_comorbidities.sql
\ir seed_occupations.sql
\ir seed_nationalities.sql
\ir seed_healthfacilities.sql
\ir seed_healthfacility_raw_map.sql
