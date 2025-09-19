BEGIN;

ALTER TABLE ingestion_run
  ADD COLUMN summary JSONB;

COMMIT;
