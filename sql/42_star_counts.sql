-- 42_star_counts.sql: row counts of every warehouse table (written to results/star_counts.csv)
SELECT 'dim_ship' AS table_name, count(*) AS row_count FROM dw.dim_ship
UNION ALL SELECT 'dim_time', count(*) FROM dw.dim_time
UNION ALL SELECT 'dim_cell', count(*) FROM dw.dim_cell
UNION ALL SELECT 'dim_nav_status', count(*) FROM dw.dim_nav_status
UNION ALL SELECT 'fact_position', count(*) FROM dw.fact_position
UNION ALL SELECT 'fact_trip', count(*) FROM dw.fact_trip;
