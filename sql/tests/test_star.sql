-- test_star.sql: integrity checks for M4. Run with -v trip_gap=30. Fails loudly on any problem.
-- (Orphan keys are already impossible: the foreign keys added in 41_star_etl.sql validate them.)
\set ON_ERROR_STOP on
SELECT set_config('test.trip_gap', :'trip_gap', false);
DO $$
DECLARE gap int := current_setting('test.trip_gap')::int;
BEGIN
    IF (SELECT count(*) FROM dw.fact_position) <> (SELECT count(*) FROM clean.ais) THEN
        RAISE EXCEPTION 'fact_position rows <> clean.ais rows';
    END IF;
    IF (SELECT count(*) FROM dw.dim_ship) <> (SELECT count(DISTINCT mmsi) FROM clean.ais) THEN
        RAISE EXCEPTION 'dim_ship rows <> distinct MMSI in clean.ais';
    END IF;
    IF (SELECT count(*) FROM dw.fact_trip) <> (SELECT count(*) FROM mobility.trips WHERE gap_minutes = gap) THEN
        RAISE EXCEPTION 'fact_trip rows <> trips for gap %', gap;
    END IF;
    IF (SELECT count(*) FROM dw.dim_time) <> 24 THEN RAISE EXCEPTION 'dim_time must have 24 hours'; END IF;
    IF (SELECT count(*) FROM dw.dim_cell) <> 24 * 60 THEN RAISE EXCEPTION 'dim_cell must have 1440 cells'; END IF;
    IF EXISTS (SELECT 1 FROM dw.fact_position f JOIN dw.dim_cell c USING (cell_key)
               WHERE NOT ST_Intersects(f.geom, c.geom) LIMIT 1) THEN
        RAISE EXCEPTION 'a position lies outside its grid cell';
    END IF;
    IF EXISTS (SELECT 1 FROM dw.fact_trip WHERE length_km < 0 OR duration_min <= 0) THEN
        RAISE EXCEPTION 'trip with negative length or non-positive duration';
    END IF;
    RAISE NOTICE 'test_star: all checks passed';
END $$;
