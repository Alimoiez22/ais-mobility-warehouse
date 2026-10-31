-- test_clean.sql: row-count and rule tests for M2. Fails loudly (RAISE EXCEPTION) on any problem.
DO $$
DECLARE
    n_clean   bigint;
    n_staging bigint;
    broken    int;
BEGIN
    SELECT count(*) INTO n_clean FROM clean.ais;
    SELECT count(*) INTO n_staging FROM staging.ais_raw;

    -- 1. The log starts from the full staging table.
    IF (SELECT rows_before FROM clean.cleaning_log WHERE step = 0) <> n_staging THEN
        RAISE EXCEPTION 'step 0 rows_before does not equal staging row count %', n_staging;
    END IF;

    -- 2. Each step starts where the previous one ended.
    SELECT count(*) INTO broken
    FROM clean.cleaning_log a JOIN clean.cleaning_log b ON b.step = a.step + 1
    WHERE b.rows_before <> a.rows_after;
    IF broken > 0 THEN RAISE EXCEPTION 'cleaning log chain broken at % step(s)', broken; END IF;

    -- 3. The last step's rows_after is the real table size.
    IF (SELECT rows_after FROM clean.cleaning_log ORDER BY step DESC LIMIT 1) <> n_clean THEN
        RAISE EXCEPTION 'last logged rows_after does not equal clean.ais count %', n_clean;
    END IF;

    -- 4. Each rule actually holds on the result.
    IF EXISTS (SELECT 1 FROM clean.ais GROUP BY row_hash HAVING count(*) > 1) THEN
        RAISE EXCEPTION 'rule 1: exact duplicates remain';
    END IF;
    IF EXISTS (SELECT 1 FROM clean.ais WHERE type_of_mobile NOT IN ('Class A', 'Class B')) THEN
        RAISE EXCEPTION 'rule 2: non-vessel transmitters remain';
    END IF;
    IF EXISTS (SELECT 1 FROM clean.ais WHERE mmsi NOT BETWEEN 200000000 AND 799999999) THEN
        RAISE EXCEPTION 'rule 3: invalid MMSIs remain';
    END IF;
    IF EXISTS (SELECT 1 FROM clean.ais WHERE NOT (lat BETWEEN 53 AND 59 AND lon BETWEEN 2 AND 17)) THEN
        RAISE EXCEPTION 'rule 4: positions outside the study area remain';
    END IF;
    IF EXISTS (SELECT 1 FROM clean.ais GROUP BY mmsi, ts_utc HAVING count(*) > 1) THEN
        RAISE EXCEPTION 'rule 5: same ship at the same second remains';
    END IF;

    -- 5. No row is lost without being counted.
    IF n_staging - (SELECT sum(rows_removed) FROM clean.cleaning_log) <> n_clean THEN
        RAISE EXCEPTION 'removed rows do not add up';
    END IF;

    RAISE NOTICE 'test_clean: all checks passed (% of % rows kept)', n_clean, n_staging;
END $$;
