-- 32_trips_compare.sql: compare the gap values (written to results/trips_compare.csv).
-- Lengths are geodesic (metres on the WGS84 ellipsoid): the trip's path as a PostGIS
-- geography. (MobilityDB's transform() to a metric projection failed with a PROJ
-- "invalid coordinate" error on this data, so the projection step is avoided.)
-- "Implausible" = the trip's average speed (length / duration) exceeds 50 knots,
-- a sanity flag for position jumps, not a cleaning rule.
WITH t AS (
    SELECT gap_minutes, mmsi, n_points, numInstants(trip) AS stored_instants,
           extract(epoch FROM end_ts - start_ts) / 60.0          AS duration_min,
           ST_Length(trajectory(trip)::geography) / 1000.0       AS length_km
    FROM mobility.trips
)
SELECT t.gap_minutes,
       s.segments                                                          AS segments_total,
       s.single_point                                                      AS single_report_segments,
       count(*)                                                            AS trips,
       count(DISTINCT mmsi)                                                AS ships,
       sum(n_points)                                                       AS points_in_trips,
       sum(stored_instants)                                                AS instants_after_normalisation,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY n_points)               AS median_points,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY duration_min)::numeric, 1) AS median_duration_min,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY length_km)::numeric, 2)    AS median_length_km,
       round(sum(length_km)::numeric, 0)                                   AS total_length_km,
       count(*) FILTER (WHERE duration_min > 0
                          AND length_km / (duration_min / 60.0) / 1.852 > 50)  AS trips_avg_speed_over_50kn
FROM t JOIN mobility.trip_segments s USING (gap_minutes)
GROUP BY t.gap_minutes, s.segments, s.single_point
ORDER BY t.gap_minutes;
