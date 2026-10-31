-- Q3: Which 0.25-degree grid cells see the most distinct ships during the day?
SELECT c.cell_key,
       round((c.lat_min + 0.125)::numeric, 3) AS center_lat,
       round((c.lon_min + 0.125)::numeric, 3) AS center_lon,
       count(DISTINCT f.ship_key)             AS ships,
       count(*)                               AS reports
FROM dw.fact_position f
JOIN dw.dim_cell c USING (cell_key)
GROUP BY c.cell_key, c.lat_min, c.lon_min
ORDER BY ships DESC
LIMIT 10;
