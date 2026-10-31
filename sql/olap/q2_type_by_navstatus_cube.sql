-- Q2: Which combinations of ship type and navigational status occur, with all subtotals? (CUBE)
SELECT coalesce(s.ship_type, '(all types)')     AS ship_type,
       coalesce(n.nav_status, '(all statuses)') AS nav_status,
       count(*)                                 AS reports,
       count(DISTINCT f.ship_key)               AS ships
FROM dw.fact_position f
JOIN dw.dim_ship s USING (ship_key)
JOIN dw.dim_nav_status n USING (nav_key)
GROUP BY CUBE (s.ship_type, n.nav_status)
HAVING count(*) >= 1000
ORDER BY s.ship_type NULLS LAST, reports DESC;
