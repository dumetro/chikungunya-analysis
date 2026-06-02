-- Table: public.chikungunya_analysis

-- DROP TABLE IF EXISTS public.chikungunya_analysis;

CREATE TABLE IF NOT EXISTS public.chikungunya_analysis
(
    id integer NOT NULL DEFAULT nextval('chikungunya_analysis_id_seq'::regclass),
    date_of_notification date,
    date_of_sample_taken date,
    epi_week character varying(10) COLLATE pg_catalog."default",
    active_passive character varying(50) COLLATE pg_catalog."default",
    health_region character varying(150) COLLATE pg_catalog."default",
    health_office character varying(150) COLLATE pg_catalog."default",
    locality character varying(150) COLLATE pg_catalog."default",
    age smallint,
    age_group character varying(50) COLLATE pg_catalog."default",
    gender character varying(20) COLLATE pg_catalog."default",
    nationality character varying(100) COLLATE pg_catalog."default",
    occupation character varying(150) COLLATE pg_catalog."default",
    past_history_of_chikungunya character varying(20) COLLATE pg_catalog."default",
    pregnancy character varying(20) COLLATE pg_catalog."default",
    gestation_week smallint,
    comorbidities_pmh text COLLATE pg_catalog."default",
    date_of_onset_symptoms date,
    symptoms text COLLATE pg_catalog."default",
    epi_linkage character varying(255) COLLATE pg_catalog."default",
    local_or_imported character varying(50) COLLATE pg_catalog."default",
    health_institution_attended character varying(200) COLLATE pg_catalog."default",
    date_attended date,
    health_institution character varying(200) COLLATE pg_catalog."default",
    if_admitted character varying(20) COLLATE pg_catalog."default",
    date_of_admission date,
    pcr_result character varying(50) COLLATE pg_catalog."default",
    date_of_negative_pcr date,
    outcome character varying(50) COLLATE pg_catalog."default",
    dmu_hospitalised_tba_missing character varying(50) COLLATE pg_catalog."default",
    remarks text COLLATE pg_catalog."default",
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT chikungunya_analysis_pkey PRIMARY KEY (id),
    CONSTRAINT chikungunya_analysis_age_check CHECK (age >= 0 AND age <= 120),
    CONSTRAINT chikungunya_analysis_gestation_week_check CHECK (gestation_week >= 4 AND gestation_week <= 42),
    CONSTRAINT chk_sample_after_onset CHECK (date_of_sample_taken IS NULL OR date_of_onset_symptoms IS NULL OR date_of_sample_taken >= date_of_onset_symptoms),
    CONSTRAINT chk_notification_after_onset CHECK (date_of_notification IS NULL OR date_of_onset_symptoms IS NULL OR date_of_notification >= date_of_onset_symptoms),
    CONSTRAINT chk_admission_after_attended CHECK (date_of_admission IS NULL OR date_attended IS NULL OR date_of_admission >= date_attended),
    CONSTRAINT chk_negative_pcr_after_sample CHECK (date_of_negative_pcr IS NULL OR date_of_sample_taken IS NULL OR date_of_negative_pcr >= date_of_sample_taken),
    CONSTRAINT chk_gestation_only_if_pregnant CHECK (gestation_week IS NULL OR pregnancy::text = 'Yes'::text),
    CONSTRAINT chk_admission_date_if_admitted CHECK (if_admitted::text <> 'Yes'::text OR date_of_admission IS NOT NULL)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.chikungunya_analysis
    OWNER to postgres;

COMMENT ON TABLE public.chikungunya_analysis
    IS 'Primary case-level dataset for Chikungunya surveillance analysis';
-- Index: idx_chik_age_group

-- DROP INDEX IF EXISTS public.idx_chik_age_group;

CREATE INDEX IF NOT EXISTS idx_chik_age_group
    ON public.chikungunya_analysis USING btree
    (age_group COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: idx_chik_epi_week

-- DROP INDEX IF EXISTS public.idx_chik_epi_week;

CREATE INDEX IF NOT EXISTS idx_chik_epi_week
    ON public.chikungunya_analysis USING btree
    (epi_week COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: idx_chik_gender

-- DROP INDEX IF EXISTS public.idx_chik_gender;

CREATE INDEX IF NOT EXISTS idx_chik_gender
    ON public.chikungunya_analysis USING btree
    (gender COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: idx_chik_health_region

-- DROP INDEX IF EXISTS public.idx_chik_health_region;

CREATE INDEX IF NOT EXISTS idx_chik_health_region
    ON public.chikungunya_analysis USING btree
    (health_region COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: idx_chik_local_imported

-- DROP INDEX IF EXISTS public.idx_chik_local_imported;

CREATE INDEX IF NOT EXISTS idx_chik_local_imported
    ON public.chikungunya_analysis USING btree
    (local_or_imported COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: idx_chik_locality

-- DROP INDEX IF EXISTS public.idx_chik_locality;

CREATE INDEX IF NOT EXISTS idx_chik_locality
    ON public.chikungunya_analysis USING btree
    (locality COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: idx_chik_notification_date

-- DROP INDEX IF EXISTS public.idx_chik_notification_date;

CREATE INDEX IF NOT EXISTS idx_chik_notification_date
    ON public.chikungunya_analysis USING btree
    (date_of_notification ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: idx_chik_onset_date

-- DROP INDEX IF EXISTS public.idx_chik_onset_date;

CREATE INDEX IF NOT EXISTS idx_chik_onset_date
    ON public.chikungunya_analysis USING btree
    (date_of_onset_symptoms ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: idx_chik_outcome

-- DROP INDEX IF EXISTS public.idx_chik_outcome;

CREATE INDEX IF NOT EXISTS idx_chik_outcome
    ON public.chikungunya_analysis USING btree
    (outcome COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: idx_chik_pcr_result

-- DROP INDEX IF EXISTS public.idx_chik_pcr_result;

CREATE INDEX IF NOT EXISTS idx_chik_pcr_result
    ON public.chikungunya_analysis USING btree
    (pcr_result COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;