-- 21_rule_exact_duplicates.sql  (M2, rule 1)
-- Remove rows whose 26 original columns are all identical to an earlier row.
-- The first copy (lowest row_id, i.e. earliest line in the file) is kept.
-- Why first: a copy adds no information, so removing it cannot change any answer,
-- and every later rule then counts real reports instead of copies.
--
-- Counting pattern used by every rule: the DELETE runs in a CTE; the INSERT into the
-- log sees the table as it was before the DELETE (same statement snapshot), so
-- rows_before is the true count before this rule.

WITH ranked AS (
    SELECT row_id,
           row_number() OVER (PARTITION BY row_hash ORDER BY row_id) AS copy_no
    FROM clean.ais
),
deleted AS (
    DELETE FROM clean.ais a
    USING ranked r
    WHERE a.row_id = r.row_id AND r.copy_no > 1
    RETURNING 1
)
INSERT INTO clean.cleaning_log (step, rule, description, rows_before, rows_removed)
SELECT 1, 'exact_duplicates',
       'Remove rows identical in all 26 source columns to an earlier row (keep first)',
       (SELECT count(*) FROM clean.ais), (SELECT count(*) FROM deleted);

VACUUM ANALYZE clean.ais;
