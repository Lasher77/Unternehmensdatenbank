BEGIN;

-- Example partitioning (optional)
-- ALTER TABLE company_history PARTITION BY RANGE (date_trunc('year', valid_from));
-- ALTER TABLE events PARTITION BY RANGE (event_date);

COMMIT;
