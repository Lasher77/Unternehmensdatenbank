BEGIN;
ALTER TABLE persons
  ADD CONSTRAINT persons_source_person_id_key UNIQUE (source_person_id);
COMMIT;
