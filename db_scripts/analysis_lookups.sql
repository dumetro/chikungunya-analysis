-- Table: public.analysis_lookups

-- DROP TABLE IF EXISTS public.analysis_lookups;

CREATE TABLE IF NOT EXISTS public.analysis_lookups
(
    lookup_id integer NOT NULL DEFAULT nextval('analysis_lookups_lookup_id_seq'::regclass),
    lk_category character varying(100) COLLATE pg_catalog."default" NOT NULL,
    lk_value character varying(255) COLLATE pg_catalog."default" NOT NULL,
    lk_sequence integer NOT NULL DEFAULT 0,
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT analysis_lookups_pkey PRIMARY KEY (lookup_id),
    CONSTRAINT uq_lookup_category_value UNIQUE (lk_category, lk_value)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.analysis_lookups
    OWNER to postgres;

COMMENT ON TABLE public.analysis_lookups
    IS 'Master lookup table for all categorical reference values used in chikungunya_analysis';