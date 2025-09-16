CREATE TABLE company_relations (
  cr_id BIGSERIAL PRIMARY KEY,
  source_id TEXT NOT NULL,
  related_source_id TEXT NOT NULL,
  relation_type TEXT,
  description TEXT,
  run_id BIGINT REFERENCES ingestion_run(run_id)
);

CREATE TABLE staging_company_relations (
  source_id TEXT,
  related_source_id TEXT,
  relation_type TEXT,
  description TEXT,
  run_id BIGINT
);

CREATE INDEX idx_company_relations_source ON company_relations(source_id);
CREATE INDEX idx_staging_company_relations_source ON staging_company_relations(source_id);
