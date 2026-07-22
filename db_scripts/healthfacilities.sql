-- Table: public.healthfacilities

-- DROP TABLE IF EXISTS public.healthfacilities;

CREATE SEQUENCE IF NOT EXISTS public.healthfacilities_facility_id_seq;

CREATE TABLE IF NOT EXISTS public.healthfacilities
(
    facility_id integer NOT NULL DEFAULT nextval('healthfacilities_facility_id_seq'::regclass),
    facility_name character varying(150) COLLATE pg_catalog."default" NOT NULL,
    facility_type character varying(50) COLLATE pg_catalog."default",
    health_region character varying(75) COLLATE pg_catalog."default",
    CONSTRAINT healthfacilities_pkey PRIMARY KEY (facility_id),
    CONSTRAINT uq_facility_name UNIQUE (facility_name)
)

TABLESPACE pg_default;

ALTER SEQUENCE public.healthfacilities_facility_id_seq
    OWNED BY public.healthfacilities.facility_id;

ALTER TABLE IF EXISTS public.healthfacilities
    OWNER to postgres;

COMMENT ON TABLE public.healthfacilities
    IS 'Normalised healthcare-facility reference table for chikungunya_analysis.
     Canonical Mauritius facilities used to normalise the source facility columns
     health_institution_attended and health_institution.';

COMMENT ON COLUMN public.healthfacilities.facility_type
    IS 'Regional Hospital / District Hospital / Private Hospital/Clinic /
     Private Mediclinic / Community Health Centre / Area Health Centre /
     Private Laboratory';

COMMENT ON COLUMN public.healthfacilities.health_region
    IS 'Best-effort administrative health region / district the facility serves';
