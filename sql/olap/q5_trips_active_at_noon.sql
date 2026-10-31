-- Q5: How many trips were under way at some point between 12:00 and 13:00, per ship type, and how long were they? (temporal window on trips)
SELECT s.ship_type,
       count(*)                                    AS trips,
       count(DISTINCT t.ship_key)                  AS ships,
       round(avg(t.length_km)::numeric, 1)         AS avg_length_km,
       round(avg(t.duration_min)::numeric, 0)      AS avg_duration_min
FROM dw.fact_trip t
JOIN dw.dim_ship s USING (ship_key)
WHERE t.start_ts < timestamptz '2026-10-26 13:00+00'
  AND t.end_ts   > timestamptz '2026-10-26 12:00+00'
GROUP BY s.ship_type
ORDER BY trips DESC;
