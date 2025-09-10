BEGIN;

ALTER TABLE companies
  ADD CONSTRAINT chk_coords CHECK (
    (lat IS NULL AND lng IS NULL) OR
    (lat BETWEEN -90 AND 90 AND lng BETWEEN -180 AND 180)
  );

ALTER TABLE companies
  ADD CONSTRAINT chk_country_len CHECK (char_length(country) BETWEEN 2 AND 3);

CREATE INDEX IF NOT EXISTS idx_companies_state ON companies(state);
CREATE INDEX IF NOT EXISTS idx_companies_status ON companies(status);
CREATE INDEX IF NOT EXISTS idx_companies_legal_form ON companies(legal_form);
CREATE INDEX IF NOT EXISTS idx_companies_seen_in_run ON companies(seen_in_run);

COMMIT;
