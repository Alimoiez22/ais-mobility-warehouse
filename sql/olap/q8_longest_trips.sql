-- Q8: Which were the ten longest trips of the day, by which ships, from which cell to which cell?
SELECT s.name, s.ship_type, s.mmsi,
       round(t.length_km::numeric, 1)    AS length_km,
       round(t.duration_min::numeric, 0) AS duration_min,
       round(t.avg_speed_kn::numeric, 1) AS avg_speed_kn,
       t.start_ts, t.end_ts, t.start_cell_key, t.end_cell_key
FROM dw.fact_trip t
JOIN dw.dim_ship s USING (ship_key)
ORDER BY t.length_km DESC
LIMIT 10;
