-- Seed public.symptom_raw_map from analyst-verified mappings of the unmapped
-- symptom values in data/rejects/unmapped_symptoms_20260612T004152Z.csv.
--
-- One row per (raw_value, symptom_id): a multi-symptom raw string gets one
-- INSERT per symptom it contains. Raw strings are stored verbatim; the pipeline
-- loader normalises case/whitespace at match time (_key), so casing here is for
-- provenance only.
--
-- symptom_id reference: 1 Fever, 2 Arthralgia/Joint Pain, 3 Polyarthralgia,
-- 4 Myalgia/Body Ache, 5 Rash, 9 Dizziness/Vertigo, 18 Mouth Ulcers,
-- 30 Gastrointestinal illness.
--
-- Skipped junk values (not symptoms): YES, NO, NIL, UNKNOWN, 2.
-- Idempotent: ON CONFLICT relies on uq_raw_symptom (raw_value, symptom_id).

-- Fever/Myalgia/Rash -> Fever, Myalgia, Rash
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('Fever/Myalgia/Rash', 1) ON CONFLICT (raw_value, symptom_id) DO NOTHING;
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('Fever/Myalgia/Rash', 4) ON CONFLICT (raw_value, symptom_id) DO NOTHING;
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('Fever/Myalgia/Rash', 5) ON CONFLICT (raw_value, symptom_id) DO NOTHING;

-- FEVER/LIGHT HEADED/MYALGIA/RASH -> Fever, Dizziness/Vertigo, Myalgia, Rash
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('FEVER/LIGHT HEADED/MYALGIA/RASH', 1) ON CONFLICT (raw_value, symptom_id) DO NOTHING;
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('FEVER/LIGHT HEADED/MYALGIA/RASH', 9) ON CONFLICT (raw_value, symptom_id) DO NOTHING;
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('FEVER/LIGHT HEADED/MYALGIA/RASH', 4) ON CONFLICT (raw_value, symptom_id) DO NOTHING;
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('FEVER/LIGHT HEADED/MYALGIA/RASH', 5) ON CONFLICT (raw_value, symptom_id) DO NOTHING;

-- FEVER,JOINT PAIN, BODYACHE -> Fever, Joint Pain, Myalgia
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('FEVER,JOINT PAIN, BODYACHE', 1) ON CONFLICT (raw_value, symptom_id) DO NOTHING;
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('FEVER,JOINT PAIN, BODYACHE', 2) ON CONFLICT (raw_value, symptom_id) DO NOTHING;
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('FEVER,JOINT PAIN, BODYACHE', 4) ON CONFLICT (raw_value, symptom_id) DO NOTHING;

-- FEVER/MYALGIA/RASH -> Fever, Myalgia, Rash
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('FEVER/MYALGIA/RASH', 1) ON CONFLICT (raw_value, symptom_id) DO NOTHING;
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('FEVER/MYALGIA/RASH', 4) ON CONFLICT (raw_value, symptom_id) DO NOTHING;
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('FEVER/MYALGIA/RASH', 5) ON CONFLICT (raw_value, symptom_id) DO NOTHING;

-- FEVER/POLYARTHALGIA/rash -> Fever, Polyarthralgia, Rash
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('FEVER/POLYARTHALGIA/rash', 1) ON CONFLICT (raw_value, symptom_id) DO NOTHING;
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('FEVER/POLYARTHALGIA/rash', 3) ON CONFLICT (raw_value, symptom_id) DO NOTHING;
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('FEVER/POLYARTHALGIA/rash', 5) ON CONFLICT (raw_value, symptom_id) DO NOTHING;

-- POLYARTHALGIA,MOUTH ULCERS, RASH -> Polyarthralgia, Mouth Ulcers, Rash
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('POLYARTHALGIA,MOUTH ULCERS, RASH', 3) ON CONFLICT (raw_value, symptom_id) DO NOTHING;
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('POLYARTHALGIA,MOUTH ULCERS, RASH', 18) ON CONFLICT (raw_value, symptom_id) DO NOTHING;
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('POLYARTHALGIA,MOUTH ULCERS, RASH', 5) ON CONFLICT (raw_value, symptom_id) DO NOTHING;

-- BODYACHE / FEVER -> Myalgia, Fever (slash splits; not an exception pair)
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('BODYACHE / FEVER', 1) ON CONFLICT (raw_value, symptom_id) DO NOTHING;
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('BODYACHE / FEVER', 4) ON CONFLICT (raw_value, symptom_id) DO NOTHING;

-- BODYACHE/JOINT PAIN/FEVER -> Myalgia, Joint Pain, Fever
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('BODYACHE/JOINT PAIN/FEVER', 4) ON CONFLICT (raw_value, symptom_id) DO NOTHING;
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('BODYACHE/JOINT PAIN/FEVER', 2) ON CONFLICT (raw_value, symptom_id) DO NOTHING;
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('BODYACHE/JOINT PAIN/FEVER', 1) ON CONFLICT (raw_value, symptom_id) DO NOTHING;

-- FEVER ,BODYACHE -> Fever, Myalgia
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('FEVER ,BODYACHE', 1) ON CONFLICT (raw_value, symptom_id) DO NOTHING;
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('FEVER ,BODYACHE', 4) ON CONFLICT (raw_value, symptom_id) DO NOTHING;

-- JOINT PAIN, FEVER, RASH -> Joint Pain, Fever, Rash (corrected in source file)
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('JOINT PAIN, FEVER, RASH', 2) ON CONFLICT (raw_value, symptom_id) DO NOTHING;
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('JOINT PAIN, FEVER, RASH', 1) ON CONFLICT (raw_value, symptom_id) DO NOTHING;
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('JOINT PAIN, FEVER, RASH', 5) ON CONFLICT (raw_value, symptom_id) DO NOTHING;

-- MYALGIA /FEVER -> Myalgia, Fever
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('MYALGIA /FEVER', 1) ON CONFLICT (raw_value, symptom_id) DO NOTHING;
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('MYALGIA /FEVER', 4) ON CONFLICT (raw_value, symptom_id) DO NOTHING;

-- FEVER, RASH, BODYACHE -> Fever, Rash, Myalgia
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('FEVER, RASH, BODYACHE', 1) ON CONFLICT (raw_value, symptom_id) DO NOTHING;
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('FEVER, RASH, BODYACHE', 5) ON CONFLICT (raw_value, symptom_id) DO NOTHING;
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('FEVER, RASH, BODYACHE', 4) ON CONFLICT (raw_value, symptom_id) DO NOTHING;

-- FEVER /JOINT PAIN -> Fever, Joint Pain
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('FEVER /JOINT PAIN', 1) ON CONFLICT (raw_value, symptom_id) DO NOTHING;
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('FEVER /JOINT PAIN', 2) ON CONFLICT (raw_value, symptom_id) DO NOTHING;

-- FEVER/ BODYACHE /RASHES -> Fever, Myalgia, Rash
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('FEVER/ BODYACHE /RASHES', 1) ON CONFLICT (raw_value, symptom_id) DO NOTHING;
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('FEVER/ BODYACHE /RASHES', 4) ON CONFLICT (raw_value, symptom_id) DO NOTHING;
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('FEVER/ BODYACHE /RASHES', 5) ON CONFLICT (raw_value, symptom_id) DO NOTHING;

-- JOINT PAIN, FEVER,BODYACHE -> Joint Pain, Fever, Myalgia
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('JOINT PAIN, FEVER,BODYACHE', 2) ON CONFLICT (raw_value, symptom_id) DO NOTHING;
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('JOINT PAIN, FEVER,BODYACHE', 1) ON CONFLICT (raw_value, symptom_id) DO NOTHING;
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('JOINT PAIN, FEVER,BODYACHE', 4) ON CONFLICT (raw_value, symptom_id) DO NOTHING;

-- BODYACHE, JOINT PAIN,FEVER -> Myalgia, Joint Pain, Fever
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('BODYACHE, JOINT PAIN,FEVER', 4) ON CONFLICT (raw_value, symptom_id) DO NOTHING;
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('BODYACHE, JOINT PAIN,FEVER', 2) ON CONFLICT (raw_value, symptom_id) DO NOTHING;
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('BODYACHE, JOINT PAIN,FEVER', 1) ON CONFLICT (raw_value, symptom_id) DO NOTHING;

-- RASH, JOINT PAIN, FEVER -> Rash, Joint Pain, Fever
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('RASH, JOINT PAIN, FEVER', 5) ON CONFLICT (raw_value, symptom_id) DO NOTHING;
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('RASH, JOINT PAIN, FEVER', 2) ON CONFLICT (raw_value, symptom_id) DO NOTHING;
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('RASH, JOINT PAIN, FEVER', 1) ON CONFLICT (raw_value, symptom_id) DO NOTHING;

-- MYALGIA, RASH -> Myalgia, Rash
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('MYALGIA, RASH', 4) ON CONFLICT (raw_value, symptom_id) DO NOTHING;
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('MYALGIA, RASH', 5) ON CONFLICT (raw_value, symptom_id) DO NOTHING;

-- JOINT PAIIN -> Joint Pain (typo of "JOINT PAIN")
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('JOINT PAIIN', 2) ON CONFLICT (raw_value, symptom_id) DO NOTHING;

-- BODYACHES, FEVER -> Myalgia, Fever
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('BODYACHES, FEVER', 4) ON CONFLICT (raw_value, symptom_id) DO NOTHING;
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('BODYACHES, FEVER', 1) ON CONFLICT (raw_value, symptom_id) DO NOTHING;

-- FEVER ,BODYACHES -> Fever, Myalgia
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('FEVER ,BODYACHES', 1) ON CONFLICT (raw_value, symptom_id) DO NOTHING;
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('FEVER ,BODYACHES', 4) ON CONFLICT (raw_value, symptom_id) DO NOTHING;

-- FEVER/DECREASED APPETITE -> Fever, Gastrointestinal illness
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('FEVER/DECREASED APPETITE', 1) ON CONFLICT (raw_value, symptom_id) DO NOTHING;
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('FEVER/DECREASED APPETITE', 30) ON CONFLICT (raw_value, symptom_id) DO NOTHING;

-- FEVER,CONSTIPATION,RASH -> Fever, Rash, Gastrointestinal illness
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('FEVER,CONSTIPATION,RASH', 1) ON CONFLICT (raw_value, symptom_id) DO NOTHING;
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('FEVER,CONSTIPATION,RASH', 5) ON CONFLICT (raw_value, symptom_id) DO NOTHING;
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('FEVER,CONSTIPATION,RASH', 30) ON CONFLICT (raw_value, symptom_id) DO NOTHING;

-- BODYACHE, FEVER -> Myalgia, Fever
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('BODYACHE, FEVER', 4) ON CONFLICT (raw_value, symptom_id) DO NOTHING;
INSERT INTO public.symptom_raw_map (raw_value, symptom_id) VALUES ('BODYACHE, FEVER', 1) ON CONFLICT (raw_value, symptom_id) DO NOTHING;
