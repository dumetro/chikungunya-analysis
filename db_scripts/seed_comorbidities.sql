-- Seed: public.comorbidities  (canonical comorbidity / PMH names)
-- Recovered from the canonical values in the chikungunya_analysis export
-- (data/incoming/chikungunya_analysis_clean 23Jul.xlsx): the pipeline writes the
-- reference name for every value it maps and keeps unmapped values raw, so the
-- Title Case names are the reference list; raw/free-text values (ALL CAPS,
-- typos, employer names) and junk markers (NIL, ---) are excluded and should be
-- mapped through the raw_map table instead.
-- comorbidity_category is a broad clinical grouping following the ICD-10
-- chapter (Cardiovascular includes cerebrovascular disease, ICD-10 I60-I69).
-- Idempotent: ON CONFLICT (comorbidity_name) DO UPDATE keeps the category fresh.

INSERT INTO public.comorbidities (comorbidity_name, comorbidity_category) VALUES
  ('Cardiac Disease (Unspecified)', 'Cardiovascular'),
  ('Hypertension', 'Cardiovascular'),
  ('Ischaemic Heart Disease', 'Cardiovascular'),
  ('Previous CVA / Stroke', 'Cardiovascular'),
  ('Psoriasis', 'Dermatological'),
  ('Diabetes Mellitus Type 2', 'Endocrine / Metabolic'),
  ('Dyslipidaemia', 'Endocrine / Metabolic'),
  ('Hyperthyroidism', 'Endocrine / Metabolic'),
  ('Hypothyroidism', 'Endocrine / Metabolic'),
  ('Hearing Impairment / Deafness', 'Hearing / ENT'),
  ('Bipolar Disorder', 'Mental Health'),
  ('Psychiatric Disorder (Unspecified)', 'Mental Health'),
  ('Flat Foot', 'Musculoskeletal'),
  ('Rheumatoid Arthritis', 'Musculoskeletal'),
  ('Glaucoma', 'Ophthalmological'),
  ('Bronchial Asthma', 'Respiratory'),
  ('Previous Craniotomy', 'Surgical History')
ON CONFLICT (comorbidity_name) DO UPDATE
  SET comorbidity_category = EXCLUDED.comorbidity_category;
