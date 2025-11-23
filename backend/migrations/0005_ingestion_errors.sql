BEGIN;

CREATE TABLE IF NOT EXISTS ingestion_errors (
  error_id BIGSERIAL PRIMARY KEY,
  run_id BIGINT REFERENCES ingestion_run(run_id),
  source_id TEXT,
  line_number BIGINT,
  file_name TEXT NOT NULL,
  error_code TEXT NOT NULL,
  error_message TEXT,
  raw_excerpt TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ingestion_errors_run_id ON ingestion_errors(run_id);

COMMIT;
