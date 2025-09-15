BEGIN;

CREATE TABLE IF NOT EXISTS company_industries (
  ci_id BIGSERIAL PRIMARY KEY,
  source_id TEXT NOT NULL,
  scheme TEXT NOT NULL,
  code TEXT NOT NULL,
  run_id BIGINT REFERENCES ingestion_run(run_id)
);

CREATE INDEX IF NOT EXISTS idx_company_industries_source ON company_industries(source_id);
CREATE INDEX IF NOT EXISTS idx_company_industries_scheme_code ON company_industries(scheme, code);

COMMIT;
