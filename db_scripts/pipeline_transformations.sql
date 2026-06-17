-- Append-only audit table recording data-lineage transformations applied by the
-- pipeline (SN-keyed corrections and reference/lookup normalisations).
-- Idempotent: the pipeline also ensures this table at load time.

CREATE TABLE IF NOT EXISTS public.pipeline_transformations
(
    id          bigserial PRIMARY KEY,
    run_id      text NOT NULL,
    source_file text,
    sn          text,
    source_row  integer,
    stage       text NOT NULL,           -- correction | normalize
    column_name text,
    action      text NOT NULL,           -- move_in<-/move_out->/clear/set/normalize
    old_value   text,
    new_value   text,
    applied_at  timestamptz NOT NULL DEFAULT now()
)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.pipeline_transformations OWNER to postgres;

COMMENT ON TABLE public.pipeline_transformations
    IS 'Data-lineage audit log: one row per transformation applied to a source row';

CREATE INDEX IF NOT EXISTS idx_pt_sn ON public.pipeline_transformations (sn);
CREATE INDEX IF NOT EXISTS idx_pt_column ON public.pipeline_transformations (column_name);
CREATE INDEX IF NOT EXISTS idx_pt_run ON public.pipeline_transformations (run_id);
CREATE INDEX IF NOT EXISTS idx_pt_action ON public.pipeline_transformations (action);
