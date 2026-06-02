-- Table: public.occupation_raw_map

-- DROP TABLE IF EXISTS public.occupation_raw_map;

CREATE TABLE IF NOT EXISTS public.occupation_raw_map
(
    raw_value text COLLATE pg_catalog."default" NOT NULL,
    occupation_id integer NOT NULL,
    CONSTRAINT uq_raw_value UNIQUE (raw_value),
    CONSTRAINT occupation_raw_map_occupation_id_fkey FOREIGN KEY (occupation_id)
        REFERENCES public.occupations (occupation_id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.occupation_raw_map
    OWNER to postgres;

COMMENT ON TABLE public.occupation_raw_map
    IS 'Maps raw/dirty occupation strings from source data to normalised occupation_id';