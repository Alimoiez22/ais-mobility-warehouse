-- 26_rule_position_jumps.sql  (M2, rule 6). Run with -v max_kn=60.
-- Remove isolated position jumps: a report whose implied speed FROM the ship's previous
-- report AND TO its next report are both above :max_kn knots.
--
-- Why: rules 1-5 check each report on its own, so a position that is valid by itself but
-- far from where the ship was a moment ago survives. The first full run showed cargo ships
-- "travelling" 3,867 km in a day at an average of 87 knots. A single wrong position creates
-- two impossible speeds (jumping there and jumping back); requiring BOTH removes the bad
-- point and keeps its correct neighbours.
-- Limitation: a ship whose positions are wrong for a long stretch (sustained offset, e.g.
-- GNSS spoofing) has only one impossible speed at each end and is not caught.
--
-- Distance: haversine on a sphere of radius 6,371,008.8 m (mean Earth radius). Plain SQL,
-- so this rule does not depend on PostGIS. Rule 5 guarantees timestamps strictly increase,
-- so the time difference is never zero.

CREATE OR REPLACE FUNCTION clean.haversine_m(lat1 double precision, lon1 double precision,
                                             lat2 double precision, lon2 double precision)
RETURNS double precision LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT 2 * 6371008.8 * asin(least(1, sqrt(
        sin(radians(lat2 - lat1) / 2) ^ 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(radians(lon2 - lon1) / 2) ^ 2)))
$$;

WITH neighbours AS (
    SELECT row_id, lat, lon, ts_utc,
           lag(lat)     OVER w AS prev_lat, lag(lon)     OVER w AS prev_lon, lag(ts_utc)  OVER w AS prev_ts,
           lead(lat)    OVER w AS next_lat, lead(lon)    OVER w AS next_lon, lead(ts_utc) OVER w AS next_ts
    FROM clean.ais
    WINDOW w AS (PARTITION BY mmsi ORDER BY ts_utc)
),
speeds AS (
    SELECT row_id,
           clean.haversine_m(prev_lat, prev_lon, lat, lon) / extract(epoch FROM ts_utc - prev_ts) * 1.943844 AS kn_in,
           clean.haversine_m(lat, lon, next_lat, next_lon) / extract(epoch FROM next_ts - ts_utc) * 1.943844 AS kn_out
    FROM neighbours
    WHERE prev_ts IS NOT NULL AND next_ts IS NOT NULL
),
deleted AS (
    DELETE FROM clean.ais a
    USING speeds s
    WHERE a.row_id = s.row_id AND s.kn_in > :max_kn AND s.kn_out > :max_kn
    RETURNING 1
)
INSERT INTO clean.cleaning_log (step, rule, description, rows_before, rows_removed)
SELECT 6, 'position_jumps',
       'Remove isolated jumps: implied speed into and out of the report both above ' || :max_kn || ' knots',
       (SELECT count(*) FROM clean.ais), (SELECT count(*) FROM deleted);

VACUUM ANALYZE clean.ais;
