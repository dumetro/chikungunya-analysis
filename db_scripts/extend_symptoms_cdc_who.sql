-- Extend public.symptoms with CDC/WHO chikungunya symptoms.
--
-- 1) Adds category/description metadata columns (the base table only had
--    symptom_id + symptom_name).
-- 2) Inserts the symptoms from the CDC/WHO reference list that are NOT already
--    represented under a different name. Of the 9 reference symptoms, 7 already
--    exist (Fever, Arthralgia / Joint Pain, Rash, Myalgia / Body Ache, Headache,
--    Weakness / Fatigue, Nausea), so only the 2 net-new ones are inserted here.
--
-- Idempotent: safe to re-run.

ALTER TABLE IF EXISTS public.symptoms
    ADD COLUMN IF NOT EXISTS category    character varying(50),
    ADD COLUMN IF NOT EXISTS description text;

COMMENT ON COLUMN public.symptoms.category
    IS 'Clinical grouping (e.g. Primary / Secondary) per CDC/WHO chikungunya guidance.';
COMMENT ON COLUMN public.symptoms.description
    IS 'Free-text clinical description of the symptom.';

INSERT INTO public.symptoms (symptom_name, category, description) VALUES
    ('Joint Swelling',  'Primary',   'Visible inflammation and swelling in the affected joints'),
    ('Conjunctivitis',  'Secondary', 'Red eyes and mild eye irritation')
ON CONFLICT (symptom_name) DO NOTHING;

-- Backfill category/description for the pre-existing symptoms.
-- Categories: Primary = chikungunya hallmark signs; Secondary = other common
-- signs; Severe = atypical/severe manifestation; Other = non-symptom marker.
-- Matched by symptom_name, so rows added above are left untouched; idempotent.
UPDATE public.symptoms AS s
SET category    = v.category,
    description = v.description
FROM (VALUES
    ('Fever',                       'Primary',   'Elevated body temperature, often abrupt and exceeding 39°C (102°F)'),
    ('Arthralgia / Joint Pain',     'Primary',   'Pain and stiffness in the joints, frequently debilitating'),
    ('Polyarthralgia',              'Primary',   'Pain affecting multiple joints simultaneously, often symmetrical'),
    ('Myalgia / Body Ache',         'Primary',   'Generalised muscle pain and body aches'),
    ('Rash',                        'Primary',   'Maculopapular skin rash, typically on the trunk and limbs'),
    ('Headache',                    'Secondary', 'Frequent and often intense headache'),
    ('Weakness / Fatigue',          'Secondary', 'Extreme tiredness and weakness that may linger for weeks'),
    ('Chills',                      'Secondary', 'Shivering and a sensation of cold, often accompanying fever'),
    ('Dizziness / Vertigo',         'Secondary', 'Light-headedness or a spinning sensation'),
    ('Nausea',                      'Secondary', 'Feeling of sickness with an urge to vomit'),
    ('Vomiting',                    'Secondary', 'Forceful expulsion of stomach contents'),
    ('Diarrhoea',                   'Secondary', 'Loose or watery stools'),
    ('Cough',                       'Secondary', 'Respiratory cough'),
    ('Sore Throat',                 'Secondary', 'Pain or irritation in the throat'),
    ('Itching',                     'Secondary', 'Pruritus, often associated with rash'),
    ('Pedal Oedema / Leg Swelling', 'Secondary', 'Swelling of the feet and lower legs due to fluid retention'),
    ('Skin Lesions',                'Secondary', 'Localised abnormal skin changes such as blisters or ulcers'),
    ('Mouth Ulcers',                'Secondary', 'Painful sores in the oral mucosa'),
    ('Neck Pain',                   'Secondary', 'Pain and stiffness in the neck'),
    ('Low Back Pain',               'Secondary', 'Pain in the lower back region'),
    ('Leg Pain',                    'Secondary', 'Pain in the legs'),
    ('Knee Pain',                   'Secondary', 'Pain localised to the knee joint'),
    ('Ankle Pain',                  'Secondary', 'Pain localised to the ankle joint'),
    ('Difficulty Mobilising',       'Secondary', 'Impaired movement or walking due to joint or muscle pain'),
    ('Loss of Consciousness',       'Severe',    'Fainting or loss of consciousness; an atypical/severe manifestation'),
    ('Hypotension',                 'Severe',    'Abnormally low blood pressure; an atypical/severe manifestation'),
    ('Asymptomatic',                'Other',     'No symptoms reported')
) AS v(symptom_name, category, description)
WHERE s.symptom_name = v.symptom_name;
