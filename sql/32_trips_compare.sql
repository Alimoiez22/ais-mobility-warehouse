-- 32_trips_compare.sql: compare the gap values (written to results/trips_compare.csv).
-- Lengths and speeds are computed in ETRS89 / UTM zone 32N (EPSG:25832), a metric
-- projection for Denmark, because degrees are not a distance.
-- "Implausible" = the trip's maximum computed speed exceeds 50 knots (25.7 m/s),
-- a sanity flag for position jumps, not a cleaning rule.
WITH t AS (
    SELECT gap_minutes, mmsi, n_points,
           extract(epoch FROM end_ts - start_ts) / 60.0          AS duration_min,
           length(transform(trip, 25832)) / 1000.0               AS length_km,
           maxValue(speed(transform(trip, 25832)))               AS max_speed_ms
    FROM mobility.trips
)
SELECT t.gap_minutes,
       s.segments                                                          AS segments_total,
       s.single_point                                                      AS single_report_segments,
       count(*)                                                            AS trips,
       count(DISTINCT mmsi)                                                AS ships,
       sum(n_points)                                                       AS points_in_trips,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY n_points)               AS median_points,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY duration_min)::numeric, 1) AS median_duration_min,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY length_km)::numeric, 2)    AS median_length_km,
       round(sum(length_km)::numeric, 0)                                   AS total_length_km,
       count(*) FILTER (WHERE max_speed_ms > 25.7)                         AS trips_max_speed_over_50kn
FROM t JOIN mobility.trip_segments s USING (gap_minutes)
GROUP BY t.gap_minutes, s.segments, s.single_point
ORDER BY t.gap_minutes;
