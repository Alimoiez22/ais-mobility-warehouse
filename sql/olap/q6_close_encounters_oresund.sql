-- Q6: Which pairs of moving ships came within 500 m of each other in the same minute in the Øresund between 07:00 and 09:00? (proximity)
WITH p AS (   -- one position per ship per minute, ships under way only (reported speed > 1 knot)
    SELECT DISTINCT ON (f.ship_key, date_trunc('minute', f.ts))
           f.ship_key, date_trunc('minute', f.ts) AS minute, f.geom
    FROM dw.fact_position f
    WHERE f.geom && ST_MakeEnvelope(12.45, 55.55, 12.85, 56.10, 4326)
      AND f.ts >= timestamptz '2026-10-26 07:00+00' AND f.ts < timestamptz '2026-10-26 09:00+00'
      AND f.sog_kn > 1
    ORDER BY f.ship_key, date_trunc('minute', f.ts), f.ts
),
pairs AS (
    SELECT a.ship_key AS ship_a, b.ship_key AS ship_b, a.minute,
           ST_Distance(a.geom::geography, b.geom::geography) AS distance_m
    FROM p a JOIN p b ON a.minute = b.minute AND a.ship_key < b.ship_key
    WHERE ST_DWithin(a.geom::geography, b.geom::geography, 500)
)
SELECT sa.name AS ship_a, sa.ship_type AS type_a, sb.name AS ship_b, sb.ship_type AS type_b,
       min(pairs.minute) AS first_minute, count(*) AS minutes_within_500m,
       round(min(distance_m)::numeric, 0) AS closest_m
FROM pairs
JOIN dw.dim_ship sa ON sa.ship_key = pairs.ship_a
JOIN dw.dim_ship sb ON sb.ship_key = pairs.ship_b
GROUP BY sa.name, sa.ship_type, sb.name, sb.ship_type
ORDER BY closest_m
LIMIT 20;
