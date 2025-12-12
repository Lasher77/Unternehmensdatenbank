DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'persons_source_person_id_key'
  ) THEN
    ALTER TABLE persons
      ADD CONSTRAINT persons_source_person_id_key UNIQUE (source_person_id);
  END IF;
END $$;
