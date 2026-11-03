-- 45_trip_tracks.sql: one simplified line per trip, for the dashboard map
-- (written to data/trip_tracks.csv by `make dashboard`; regenerated, never committed).
--
-- * Source: dw.fact_trip (gap 30 min), whose traj column is the trip as a geometry.
-- * ST_SimplifyPreserveTopology with a 0.001 degree tolerance (about 60-110 m here)
--   keeps the shape of each route while cutting the point count, so the page stays small.
-- * Left out: trips that never moved (traj is a point), trips shorter than 0.5 km
--   (ships at anchor or in port drift a few metres), and trips whose average speed is
--   above 50 knots. No ship in these waters averages that over a whole trip, so those
--   lines are leftover position errors that rule 6 does not catch (see decision 11b).

SELECT t.trip_key,
       s.ship_type,
       coalesce(s.name, '')                              AS name,
       round(t.length_km::numeric, 1)                    AS length_km,
       round(t.duration_min::numeric)                    AS duration_min,
       round(t.avg_speed_kn::numeric, 1)                 AS avg_speed_kn,
       to_char(t.start_ts AT TIME ZONE 'UTC', 'HH24:MI') AS start_utc,
       to_char(t.end_ts   AT TIME ZONE 'UTC', 'HH24:MI') AS end_utc,
       ST_AsGeoJSON(ST_SimplifyPreserveTopology(t.traj, 0.001), 4) AS geojson
FROM dw.fact_trip t
JOIN dw.dim_ship s USING (ship_key)
WHERE GeometryType(t.traj) = 'LINESTRING'
  AND t.length_km >= 0.5
  AND (t.avg_speed_kn IS NULL OR t.avg_speed_kn <= 50)
ORDER BY t.trip_key;
