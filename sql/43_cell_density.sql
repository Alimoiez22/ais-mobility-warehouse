-- 43_cell_density.sql: ships and reports per grid cell, for the dashboard map
-- (written to results/cell_density.csv). Cells with no reports are left out.
SELECT c.cell_key, c.lat_min, c.lon_min,
       count(DISTINCT f.ship_key) AS ships,
       count(*)                   AS reports
FROM dw.fact_position f
JOIN dw.dim_cell c USING (cell_key)
GROUP BY c.cell_key, c.lat_min, c.lon_min
ORDER BY c.cell_key;
