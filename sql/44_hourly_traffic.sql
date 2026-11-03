-- 44_hourly_traffic.sql: reports and distinct ships per hour of the day, for the dashboard
-- (written to results/hourly_traffic.csv).
SELECT t.hour, t.day_part,
       count(*)                   AS reports,
       count(DISTINCT f.ship_key) AS ships
FROM dw.fact_position f
JOIN dw.dim_time t USING (time_key)
GROUP BY t.hour, t.day_part
ORDER BY t.hour;
