-- Table: public.occupations

-- DROP TABLE IF EXISTS public.occupations;

CREATE TABLE IF NOT EXISTS public.occupations
(
    occupation_id integer NOT NULL DEFAULT nextval('occupations_occupation_id_seq'::regclass),
    occupation_name character varying(150) COLLATE pg_catalog."default" NOT NULL,
    CONSTRAINT occupations_pkey PRIMARY KEY (occupation_id),
    CONSTRAINT uq_occupation_name UNIQUE (occupation_name)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.occupations
    OWNER to postgres;

COMMENT ON TABLE public.occupations
    IS 'Normalised occupation reference table for chikungunya_analysis';