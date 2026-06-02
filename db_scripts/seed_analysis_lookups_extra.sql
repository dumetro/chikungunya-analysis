-- Additional canonical analysis_lookups values discovered while cleaning the
-- 2026 Mauritius dataset. Idempotent: re-running is safe.
--
-- "Active" outcome = case still ongoing (no final outcome recorded yet). It is
-- the dominant real value in the source OUTCOME column (~306 cases) and was
-- missing from the seed list.

INSERT INTO public.analysis_lookups (lk_category, lk_value, lk_sequence, is_active)
VALUES ('OUTCOME', 'Active', 6, true)
ON CONFLICT (lk_category, lk_value) DO NOTHING;

-- Add further canonical values here as the unmapped-values report surfaces them,
-- e.g.:
-- INSERT INTO public.analysis_lookups (lk_category, lk_value, lk_sequence, is_active)
-- VALUES ('PCR_RESULT', 'Inconclusive', 5, true)
-- ON CONFLICT (lk_category, lk_value) DO NOTHING;
