-- Seed: public.analysis_lookups  (base canonical values per category)
-- Categories are the lookup_columns in config/column_mapping.yaml; values mirror
-- the allowed_sets in config/expectations.yaml. Run before
-- seed_analysis_lookups_extra.sql, which continues OUTCOME at lk_sequence 6.
-- Idempotent: ON CONFLICT (lk_category, lk_value) DO NOTHING.

INSERT INTO public.analysis_lookups (lk_category, lk_value, lk_sequence, is_active) VALUES
  ('GENDER', 'Male', 1, true),
  ('GENDER', 'Female', 2, true),
  ('GENDER', 'Unknown', 3, true),
  ('AGE_GROUP', '0-19', 1, true),
  ('AGE_GROUP', '20-39', 2, true),
  ('AGE_GROUP', '40-59', 3, true),
  ('AGE_GROUP', '60-150', 4, true),
  ('ACTIVE_PASSIVE', 'Active', 1, true),
  ('ACTIVE_PASSIVE', 'Passive', 2, true),
  ('LOCAL_IMPORTED', 'Local', 1, true),
  ('LOCAL_IMPORTED', 'Imported', 2, true),
  ('LOCAL_IMPORTED', 'Unknown', 3, true),
  ('PCR_RESULT', 'Positive', 1, true),
  ('PCR_RESULT', 'Negative', 2, true),
  ('PCR_RESULT', 'Pending', 3, true),
  ('PCR_RESULT', 'Not Done', 4, true),
  ('OUTCOME', 'Alive', 1, true),
  ('OUTCOME', 'Deceased', 2, true),
  ('OUTCOME', 'Lost to Follow-up', 3, true),
  ('OUTCOME', 'Discharged', 4, true),
  ('OUTCOME', 'Unknown', 5, true)
ON CONFLICT (lk_category, lk_value) DO NOTHING;
