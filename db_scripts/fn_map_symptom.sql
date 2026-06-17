-- FUNCTION: public.fn_map_symptom(text, text)

-- DROP FUNCTION IF EXISTS public.fn_map_symptom(text, text);

CREATE OR REPLACE FUNCTION public.fn_map_symptom(
	p_raw text,
	p_symptom text)
    RETURNS void
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
AS $BODY$
BEGIN
    INSERT INTO symptom_raw_map (raw_value, symptom_id)
    SELECT p_raw, symptom_id
    FROM symptoms
    WHERE symptom_name = p_symptom
    ON CONFLICT DO NOTHING;
END;
$BODY$;

ALTER FUNCTION public.fn_map_symptom(text, text)
    OWNER TO postgres;
