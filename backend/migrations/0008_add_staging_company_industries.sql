-- Migration to add staging_company_industries table
CREATE TABLE IF NOT EXISTS staging_company_industries (
    source_id TEXT,
    scheme TEXT,
    code TEXT,
    run_id BIGINT
);

CREATE INDEX IF NOT EXISTS idx_staging_company_industries_source
    ON staging_company_industries(source_id);
