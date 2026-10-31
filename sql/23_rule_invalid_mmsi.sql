-- 23_rule_invalid_mmsi.sql  (M2, rule 3)
-- Keep only MMSIs with the ship format: 9 digits whose first digit is 2-7
-- (the first three digits are the country code, ITU numbering scheme).
-- Why: the MMSI is the ship's key in the warehouse. A malformed key (wrong length,
-- test or default IDs) cannot be linked to one real vessel.

WITH deleted AS (
    DELETE FROM clean.ais
    WHERE mmsi NOT BETWEEN 200000000 AND 799999999
    RETURNING 1
)
INSERT INTO clean.cleaning_log (step, rule, description, rows_before, rows_removed)
SELECT 3, 'invalid_ship_mmsi',
       'Remove MMSIs that are not 9 digits starting with 2-7',
       (SELECT count(*) FROM clean.ais), (SELECT count(*) FROM deleted);

VACUUM ANALYZE clean.ais;
