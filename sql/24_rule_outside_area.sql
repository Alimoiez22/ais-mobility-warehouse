-- 24_rule_outside_area.sql  (M2, rule 4)
-- Keep positions inside the study area: latitude 53-59 N, longitude 2-17 E.
-- This box covers Danish waters, Skagerrak, Kattegat, the Danish straits and the
-- western Baltic around the DMA receiver network.
-- It also removes the AIS "position not available" code (latitude 91, longitude 181)
-- and positions on the other side of the globe (profile: latitude down to -64.9,
-- longitude up to 135.3), which cannot have been received by Danish shore stations.

WITH deleted AS (
    DELETE FROM clean.ais
    WHERE NOT (lat BETWEEN 53 AND 59 AND lon BETWEEN 2 AND 17)
    RETURNING 1
)
INSERT INTO clean.cleaning_log (step, rule, description, rows_before, rows_removed)
SELECT 4, 'outside_study_area',
       'Remove positions outside 53-59 N, 2-17 E (includes the latitude-91 not-available code)',
       (SELECT count(*) FROM clean.ais), (SELECT count(*) FROM deleted);

VACUUM ANALYZE clean.ais;
