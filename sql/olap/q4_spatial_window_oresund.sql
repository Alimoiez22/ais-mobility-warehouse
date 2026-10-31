-- Q4: Which ship types used the Øresund strait (55.55-56.10 N, 12.45-12.85 E) during the morning rush 07:00-09:00? (spatial + temporal window)
SELECT s.ship_type,
       count(DISTINCT f.ship_key) AS ships,
       count(*)                   AS reports,
       round(avg(f.sog_kn)::numeric, 1) AS avg_reported_speed_kn
FROM dw.fact_position f
JOIN dw.dim_ship s USING (ship_key)
WHERE f.geom && ST_MakeEnvelope(12.45, 55.55, 12.85, 56.10, 4326)
  AND f.ts >= timestamptz '2026-10-26 07:00+00' AND f.ts < timestamptz '2026-10-26 09:00+00'
GROUP BY s.ship_type
ORDER BY ships DESC;
