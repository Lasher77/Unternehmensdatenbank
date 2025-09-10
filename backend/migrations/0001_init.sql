BEGIN;

CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS postgis;

-- Importläufe
CREATE TABLE IF NOT EXISTS ingestion_run (
  run_id BIGSERIAL PRIMARY KEY,
  source VARCHAR(50) NOT NULL,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at TIMESTAMPTZ,
  notes TEXT
);

-- Aktuelle Unternehmen
CREATE TABLE IF NOT EXISTS companies (
  company_id BIGSERIAL PRIMARY KEY,
  source_id TEXT UNIQUE NOT NULL,
  raw_name TEXT,
  legal_form TEXT,
  name_norm TEXT,
  street TEXT,
  postal_code TEXT,
  city TEXT,
  state TEXT,
  country TEXT DEFAULT 'DE',
  lat DOUBLE PRECISION,
  lng DOUBLE PRECISION,
  geom GEOGRAPHY(POINT),
  register_id TEXT,
  register_city TEXT,
  register_country TEXT,
  register_unique_key TEXT,
  status TEXT,
  terminated BOOLEAN,
  data JSONB,
  seen_in_run BIGINT,
  missing_in_latest_dump BOOLEAN,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Historie (SCD-2)
CREATE TABLE IF NOT EXISTS company_history (
  history_id BIGSERIAL PRIMARY KEY,
  source_id TEXT NOT NULL,
  raw_name TEXT,
  legal_form TEXT,
  street TEXT,
  postal_code TEXT,
  city TEXT,
  state TEXT,
  country TEXT,
  lat DOUBLE PRECISION,
  lng DOUBLE PRECISION,
  status TEXT,
  terminated BOOLEAN,
  valid_from TIMESTAMPTZ NOT NULL,
  valid_to TIMESTAMPTZ,
  run_id BIGINT REFERENCES ingestion_run(run_id)
);

-- Ereignisse
CREATE TABLE IF NOT EXISTS events (
  event_id BIGSERIAL PRIMARY KEY,
  source_id TEXT NOT NULL,
  event_date DATE,
  event_type TEXT,
  description TEXT,
  run_id BIGINT REFERENCES ingestion_run(run_id)
);

-- Personen
CREATE TABLE IF NOT EXISTS persons (
  person_id BIGSERIAL PRIMARY KEY,
  source_person_id TEXT,
  first_name TEXT,
  last_name TEXT,
  birth_date DATE,
  data JSONB
);

CREATE TABLE IF NOT EXISTS company_person_roles (
  cpr_id BIGSERIAL PRIMARY KEY,
  source_id TEXT NOT NULL,
  person_id BIGINT REFERENCES persons(person_id),
  role_name TEXT,
  role_type TEXT,
  role_date DATE,
  run_id BIGINT REFERENCES ingestion_run(run_id)
);

-- Staging
CREATE TABLE IF NOT EXISTS staging_companies (
  source_id TEXT,
  data JSONB,
  run_id BIGINT
);

CREATE TABLE IF NOT EXISTS staging_events (
  source_id TEXT,
  event_date DATE,
  event_type TEXT,
  description TEXT,
  run_id BIGINT
);

-- Indizes
CREATE INDEX IF NOT EXISTS idx_companies_tsv ON companies USING GIN (to_tsvector('german', coalesce(raw_name,'') || ' ' || coalesce(city,'')));
CREATE INDEX IF NOT EXISTS idx_companies_trgm_rawname ON companies USING GIN (raw_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_companies_geom ON companies USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_companies_plz_city ON companies(postal_code, city);
CREATE INDEX IF NOT EXISTS idx_companies_data ON companies USING GIN (data);

CREATE INDEX IF NOT EXISTS idx_history_source ON company_history(source_id);
CREATE INDEX IF NOT EXISTS idx_history_valid_to ON company_history(valid_to);
CREATE INDEX IF NOT EXISTS idx_events_source_date ON events(source_id, event_date);
CREATE INDEX IF NOT EXISTS idx_cpr_source ON company_person_roles(source_id);

COMMIT;
