-- Add the pipeline-derived case classification column to chikungunya_analysis.
-- Idempotent: safe to re-run. The pipeline also ensures this column exists at
-- load time, so running this manually is optional.
--
-- Values: Confirmed | Probable | Suspected | Unclassified
-- (WHO/PAHO surveillance definition — see config/case_definitions.yaml).

ALTER TABLE public.chikungunya_analysis
    ADD COLUMN IF NOT EXISTS case_classification character varying(20);

COMMENT ON COLUMN public.chikungunya_analysis.case_classification
    IS 'Derived WHO/PAHO case classification (Confirmed/Probable/Suspected/Unclassified)';

CREATE INDEX IF NOT EXISTS idx_chik_case_classification
    ON public.chikungunya_analysis USING btree
    (case_classification COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;
