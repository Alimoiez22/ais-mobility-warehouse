-- 29_cleaning_report.sql: the cleaning log as a table, written to results/cleaning.csv
SELECT step,
       rule,
       rows_before,
       rows_removed,
       rows_after,
       round(100.0 * rows_removed / NULLIF(rows_before, 0), 2)                              AS pct_of_step_input,
       round(100.0 * rows_removed / (SELECT rows_before FROM clean.cleaning_log WHERE step = 0), 2) AS pct_of_raw,
       description
FROM clean.cleaning_log
ORDER BY step;
