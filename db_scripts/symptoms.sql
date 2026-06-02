-- Table: public.symptoms

-- DROP TABLE IF EXISTS public.symptoms;

CREATE TABLE IF NOT EXISTS public.symptoms
(
    symptom_id integer NOT NULL DEFAULT nextval('symptoms_symptom_id_seq'::regclass),
    symptom_name character varying(150) COLLATE pg_catalog."default" NOT NULL,
    CONSTRAINT symptoms_pkey PRIMARY KEY (symptom_id),
    CONSTRAINT uq_symptom_name UNIQUE (symptom_name)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.symptoms
    OWNER to postgres;

COMMENT ON TABLE public.symptoms
    IS 'Normalised symptom reference table for chikungunya_analysis';