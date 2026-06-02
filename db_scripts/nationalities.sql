-- Table: public.nationalities

-- DROP TABLE IF EXISTS public.nationalities;

CREATE TABLE IF NOT EXISTS public.nationalities
(
    nationality_id integer NOT NULL DEFAULT nextval('nationalities_nationality_id_seq'::regclass),
    nationality_name character varying(100) COLLATE pg_catalog."default" NOT NULL,
    iso_alpha2 character(2) COLLATE pg_catalog."default",
    iso_alpha3 character(3) COLLATE pg_catalog."default",
    country_name character varying(100) COLLATE pg_catalog."default" NOT NULL,
    region character varying(50) COLLATE pg_catalog."default",
    sub_region character varying(75) COLLATE pg_catalog."default",
    CONSTRAINT nationalities_pkey PRIMARY KEY (nationality_id),
    CONSTRAINT uq_iso_alpha2 UNIQUE (iso_alpha2),
    CONSTRAINT uq_iso_alpha3 UNIQUE (iso_alpha3),
    CONSTRAINT uq_nationality_name UNIQUE (nationality_name)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.nationalities
    OWNER to postgres;

COMMENT ON TABLE public.nationalities
    IS 'World nationalities reference table with ISO 3166-1 country codes,
     UN geographic regions and sub-regions';

COMMENT ON COLUMN public.nationalities.iso_alpha2
    IS 'ISO 3166-1 alpha-2 two-letter country code';

COMMENT ON COLUMN public.nationalities.iso_alpha3
    IS 'ISO 3166-1 alpha-3 three-letter country code';

COMMENT ON COLUMN public.nationalities.region
    IS 'UN M.49 macro-region (Africa, Americas, Asia, Europe, Oceania)';

COMMENT ON COLUMN public.nationalities.sub_region
    IS 'UN M.49 sub-region';
-- Index: idx_nat_iso2

-- DROP INDEX IF EXISTS public.idx_nat_iso2;

CREATE INDEX IF NOT EXISTS idx_nat_iso2
    ON public.nationalities USING btree
    (iso_alpha2 COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: idx_nat_iso3

-- DROP INDEX IF EXISTS public.idx_nat_iso3;

CREATE INDEX IF NOT EXISTS idx_nat_iso3
    ON public.nationalities USING btree
    (iso_alpha3 COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: idx_nat_region

-- DROP INDEX IF EXISTS public.idx_nat_region;

CREATE INDEX IF NOT EXISTS idx_nat_region
    ON public.nationalities USING btree
    (region COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: idx_nat_sub_region

-- DROP INDEX IF EXISTS public.idx_nat_sub_region;

CREATE INDEX IF NOT EXISTS idx_nat_sub_region
    ON public.nationalities USING btree
    (sub_region COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;