-- Q7: What are the typical trip length and average speed per ship type and transponder class, with subtotals? (ROLLUP on trips)
SELECT coalesce(s.transponder, '(all classes)') AS transponder,
       coalesce(s.ship_type, '(all types)')     AS ship_type,
       count(*)                                 AS trips,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY t.length_km)::numeric, 1)    AS median_length_km,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY t.avg_speed_kn)::numeric, 1) AS median_avg_speed_kn
FROM dw.fact_trip t
JOIN dw.dim_ship s USING (ship_key)
GROUP BY ROLLUP (s.transponder, s.ship_type)
HAVING count(*) >= 20
ORDER BY s.transponder NULLS LAST, trips DESC;
