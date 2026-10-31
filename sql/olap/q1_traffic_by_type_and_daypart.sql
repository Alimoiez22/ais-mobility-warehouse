-- Q1: How is AIS traffic (reports and distinct ships) spread over ship types and parts of the day? (ROLLUP)
SELECT coalesce(s.ship_type, '(all types)')   AS ship_type,
       coalesce(t.day_part, '(whole day)')    AS day_part,
       count(*)                               AS reports,
       count(DISTINCT f.ship_key)             AS ships
FROM dw.fact_position f
JOIN dw.dim_ship s USING (ship_key)
JOIN dw.dim_time t USING (time_key)
GROUP BY ROLLUP (s.ship_type, t.day_part)
ORDER BY s.ship_type NULLS LAST, t.day_part NULLS LAST;
