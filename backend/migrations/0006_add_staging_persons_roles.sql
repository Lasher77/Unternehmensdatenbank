BEGIN;

CREATE TABLE IF NOT EXISTS staging_persons (
  source_person_id TEXT,
  data JSONB,
  run_id BIGINT
);

CREATE TABLE IF NOT EXISTS staging_company_person_roles (
  source_id TEXT,
  source_person_id TEXT,
  role_name TEXT,
  role_type TEXT,
  role_date DATE,
  run_id BIGINT
);

CREATE INDEX IF NOT EXISTS idx_staging_persons_id ON staging_persons(source_person_id);
CREATE INDEX IF NOT EXISTS idx_staging_cpr_source ON staging_company_person_roles(source_id);

COMMIT;
