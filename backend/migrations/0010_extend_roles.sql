ALTER TABLE company_person_roles
  ADD COLUMN IF NOT EXISTS description TEXT,
  ADD COLUMN IF NOT EXISTS demotion BOOLEAN;

ALTER TABLE staging_company_person_roles
  ADD COLUMN IF NOT EXISTS description TEXT,
  ADD COLUMN IF NOT EXISTS demotion BOOLEAN;
