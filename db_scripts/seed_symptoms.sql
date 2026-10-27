-- Seed: public.symptoms  (base symptom list with fixed symptom_ids)
--
-- seed_symptom_raw_map.sql hard-codes symptom_ids (1 Fever, 2 Arthralgia /
-- Joint Pain, 3 Polyarthralgia, 4 Myalgia / Body Ache, 5 Rash, 9 Dizziness /
-- Vertigo, 18 Mouth Ulcers, 30 Gastrointestinal illness), so the ids are pinned
-- here. Ids 1-27 follow the order of the backfill list in
-- extend_symptoms_cdc_who.sql, which matches every known id above. Ids 28-29
-- are unknown and left unused.
--
-- Run BEFORE extend_symptoms_cdc_who.sql: that script inserts Joint Swelling and
-- Conjunctivitis through the sequence, which setval() below moves past 30.
-- Idempotent: ON CONFLICT (symptom_id) DO NOTHING.

INSERT INTO public.symptoms (symptom_id, symptom_name) VALUES
  (1, 'Fever'),
  (2, 'Arthralgia / Joint Pain'),
  (3, 'Polyarthralgia'),
  (4, 'Myalgia / Body Ache'),
  (5, 'Rash'),
  (6, 'Headache'),
  (7, 'Weakness / Fatigue'),
  (8, 'Chills'),
  (9, 'Dizziness / Vertigo'),
  (10, 'Nausea'),
  (11, 'Vomiting'),
  (12, 'Diarrhoea'),
  (13, 'Cough'),
  (14, 'Sore Throat'),
  (15, 'Itching'),
  (16, 'Pedal Oedema / Leg Swelling'),
  (17, 'Skin Lesions'),
  (18, 'Mouth Ulcers'),
  (19, 'Neck Pain'),
  (20, 'Low Back Pain'),
  (21, 'Leg Pain'),
  (22, 'Knee Pain'),
  (23, 'Ankle Pain'),
  (24, 'Difficulty Mobilising'),
  (25, 'Loss of Consciousness'),
  (26, 'Hypotension'),
  (27, 'Asymptomatic'),
  (30, 'Gastrointestinal illness')
ON CONFLICT (symptom_id) DO NOTHING;

SELECT setval('public.symptoms_symptom_id_seq',
              GREATEST((SELECT max(symptom_id) FROM public.symptoms), 30));
