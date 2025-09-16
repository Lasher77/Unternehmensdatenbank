ALTER TABLE company_person_roles
  ADD COLUMN description TEXT,
  ADD COLUMN demotion BOOLEAN;

ALTER TABLE staging_company_person_roles
  ADD COLUMN description TEXT,
  ADD COLUMN demotion BOOLEAN;
