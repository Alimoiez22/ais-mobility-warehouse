-- 22_rule_non_vessel.sql  (M2, rule 2)
-- Keep only reports from ship transponders: 'Class A' (large ships, mandatory) and
-- 'Class B' (smaller craft). Removed: base stations, aids to navigation (AtoN),
-- SAR aircraft, SAR transponders and emergency beacons.
-- Why: the warehouse models vessel movement. A shore antenna or a buoy does not travel,
-- and an aircraft is not a vessel, so their positions would distort trips and traffic counts.

WITH deleted AS (
    DELETE FROM clean.ais
    WHERE type_of_mobile NOT IN ('Class A', 'Class B')
    RETURNING 1
)
INSERT INTO clean.cleaning_log (step, rule, description, rows_before, rows_removed)
SELECT 2, 'non_vessel_transmitter',
       'Remove reports whose type of mobile is not Class A or Class B',
       (SELECT count(*) FROM clean.ais), (SELECT count(*) FROM deleted);

VACUUM ANALYZE clean.ais;
