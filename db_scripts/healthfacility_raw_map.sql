-- Table: public.healthfacility_raw_map

-- DROP TABLE IF EXISTS public.healthfacility_raw_map;

CREATE TABLE IF NOT EXISTS public.healthfacility_raw_map
(
    raw_value text COLLATE pg_catalog."default" NOT NULL,
    facility_id integer NOT NULL,
    CONSTRAINT uq_facility_raw_value UNIQUE (raw_value),
    CONSTRAINT healthfacility_raw_map_facility_id_fkey FOREIGN KEY (facility_id)
        REFERENCES public.healthfacilities (facility_id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.healthfacility_raw_map
    OWNER to postgres;

COMMENT ON TABLE public.healthfacility_raw_map
    IS 'Maps raw/dirty health-facility strings from source data to a normalised
     facility_id. The whole (trimmed, lower-cased) source cell is the lookup key,
     matching chikungunya_pipeline.normalize._key().';
