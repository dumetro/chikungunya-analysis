-- Table: public.symptom_raw_map

-- DROP TABLE IF EXISTS public.symptom_raw_map;

CREATE TABLE IF NOT EXISTS public.symptom_raw_map
(
    id integer NOT NULL DEFAULT nextval('symptom_raw_map_id_seq'::regclass),
    raw_value text COLLATE pg_catalog."default" NOT NULL,
    symptom_id integer NOT NULL,
    CONSTRAINT symptom_raw_map_pkey PRIMARY KEY (id),
    CONSTRAINT uq_raw_symptom UNIQUE (raw_value, symptom_id),
    CONSTRAINT symptom_raw_map_symptom_id_fkey FOREIGN KEY (symptom_id)
        REFERENCES public.symptoms (symptom_id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.symptom_raw_map
    OWNER to postgres;

COMMENT ON TABLE public.symptom_raw_map
    IS 'Maps raw/dirty symptom strings to one or more normalised symptom_ids.
     One raw_value row per symptom present in that string.';