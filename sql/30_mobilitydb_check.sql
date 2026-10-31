-- 30_mobilitydb_check.sql: fail early, with a clear message, if a MobilityDB function used
-- in M3/M4 is missing (function names changed between MobilityDB versions).
DO $$
DECLARE missing text;
BEGIN
    SELECT string_agg(f, ', ') INTO missing
    FROM unnest(ARRAY['tgeompoint', 'tgeompointseq', 'trajectory', 'length', 'speed',
                      'transform', 'numinstants', 'maxvalue', 'startvalue', 'endvalue']) AS f
    WHERE NOT EXISTS (SELECT 1 FROM pg_proc WHERE proname = f);
    IF missing IS NOT NULL THEN
        RAISE EXCEPTION 'MobilityDB functions not found: %. Check SELECT extversion FROM pg_extension.', missing;
    END IF;
    RAISE NOTICE 'MobilityDB check passed (version %)',
        (SELECT extversion FROM pg_extension WHERE extname = 'mobilitydb');
END $$;
