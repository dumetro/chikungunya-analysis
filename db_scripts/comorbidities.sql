comor-- Table: public.comorbidities

-- DROP TABLE IF EXISTS public.comorbidities;

CREATE TABLE IF NOT EXISTS public.comorbidities
(
    comorbidity_id integer NOT NULL DEFAULT nextval('comorbidities_comorbidity_id_seq'::regclass),
    comorbidity_name character varying(150) COLLATE pg_catalog."default" NOT NULL,
    comorbidity_category character varying(100) COLLATE pg_catalog."default",
    CONSTRAINT comorbidities_pkey PRIMARY KEY (comorbidity_id),
    CONSTRAINT uq_comorbidity_name UNIQUE (comorbidity_name)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.comorbidities
    OWNER to postgres;

COMMENT ON TABLE public.comorbidities
    IS 'Normalised comorbidity / past medical history reference table
     for chikungunya_analysis';

COMMENT ON COLUMN public.comorbidities.comorbidity_category
    IS 'Broad clinical grouping to support category-level analysis';
-- Index: idx_comorbidity_category

-- DROP INDEX IF EXISTS public.idx_comorbidity_category;

CREATE INDEX IF NOT EXISTS idx_comorbidity_category
    ON public.comorbidities USING btree
    (comorbidity_category COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;