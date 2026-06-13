-- FUNCTION: public.fn_map_comorbidity(text, text)

-- DROP FUNCTION IF EXISTS public.fn_map_comorbidity(text, text);

CREATE OR REPLACE FUNCTION public.fn_map_comorbidity(
	p_raw text,
	p_comorbidity text)
    RETURNS void
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
AS $BODY$
BEGIN
    INSERT INTO comorbidity_raw_map (raw_value, comorbidity_id)
    SELECT p_raw, comorbidity_id
    FROM comorbidities
    WHERE comorbidity_name = p_comorbidity
    ON CONFLICT DO NOTHING;
END;
$BODY$;

ALTER FUNCTION public.fn_map_comorbidity(text, text)
    OWNER TO postgres;
