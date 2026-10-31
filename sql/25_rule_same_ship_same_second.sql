-- 25_rule_same_ship_same_second.sql  (M2, rule 5)
-- Keep one report per ship per second (the earliest line in the file).
-- After rule 1 these are reports that share MMSI and timestamp but differ in some
-- other column, typically the same message received by two shore stations.
-- Why: a trajectory needs strictly increasing timestamps; two positions for the same
-- ship at the same instant cannot both be true and break the trip construction (M3).

WITH ranked AS (
    SELECT row_id,
           row_number() OVER (PARTITION BY mmsi, ts_utc ORDER BY row_id) AS copy_no
    FROM clean.ais
),
deleted AS (
    DELETE FROM clean.ais a
    USING ranked r
    WHERE a.row_id = r.row_id AND r.copy_no > 1
    RETURNING 1
)
INSERT INTO clean.cleaning_log (step, rule, description, rows_before, rows_removed)
SELECT 5, 'same_ship_same_second',
       'Keep the first report per MMSI and timestamp',
       (SELECT count(*) FROM clean.ais), (SELECT count(*) FROM deleted);

VACUUM ANALYZE clean.ais;
