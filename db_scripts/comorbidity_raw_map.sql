-- Table: public.comorbidity_raw_map

-- DROP TABLE IF EXISTS public.comorbidity_raw_map;

CREATE SEQUENCE IF NOT EXISTS public.comorbidity_raw_map_id_seq;

CREATE TABLE IF NOT EXISTS public.comorbidity_raw_map
(
    id integer NOT NULL DEFAULT nextval('comorbidity_raw_map_id_seq'::regclass),
    raw_value text COLLATE pg_catalog."default" NOT NULL,
    comorbidity_id integer NOT NULL,
    CONSTRAINT comorbidity_raw_map_pkey PRIMARY KEY (id),
    CONSTRAINT uq_raw_comorbidity UNIQUE (raw_value, comorbidity_id),
    CONSTRAINT comorbidity_raw_map_comorbidity_id_fkey FOREIGN KEY (comorbidity_id)
        REFERENCES public.comorbidities (comorbidity_id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
)

TABLESPACE pg_default;

ALTER SEQUENCE public.comorbidity_raw_map_id_seq
    OWNED BY public.comorbidity_raw_map.id;

ALTER TABLE IF EXISTS public.comorbidity_raw_map
    OWNER to postgres;

COMMENT ON TABLE public.comorbidity_raw_map
    IS 'Maps raw/dirty comorbidity strings to one or more normalised comorbidity_ids.
     One raw_value row per comorbidity present in that string.';
