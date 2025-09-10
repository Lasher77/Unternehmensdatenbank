BEGIN;

CREATE OR REPLACE VIEW v_export_companies AS
SELECT
  c.source_id,
  COALESCE(c.name_norm, c.raw_name) AS name,
  c.legal_form,
  c.status,
  c.terminated,
  c.street,
  c.postal_code,
  c.city,
  c.state,
  c.country,
  c.lat,
  c.lng,
  c.data->>'website' AS website,
  c.data->>'email' AS email,
  c.data->>'phone' AS phone,
  c.register_id,
  c.register_city,
  c.register_country,
  c.register_unique_key,
  NULLIF(c.data#>>'{wz,0}','') AS wz,
  c.updated_at
FROM companies c;

COMMIT;
