-- test_trips.sql: sanity checks for M3. Fails loudly on any problem.
DO $$
DECLARE g int; n_clean bigint; in_trips bigint; singles bigint;
BEGIN
    SELECT count(*) INTO n_clean FROM clean.ais;
    IF NOT EXISTS (SELECT 1 FROM mobility.trips) THEN RAISE EXCEPTION 'no trips built'; END IF;

    FOR g IN SELECT DISTINCT gap_minutes FROM mobility.trips LOOP
        SELECT sum(n_points) INTO in_trips FROM mobility.trips WHERE gap_minutes = g;
        SELECT single_point INTO singles FROM mobility.trip_segments WHERE gap_minutes = g;
        -- every cleaned report is either inside a trip or a single-report segment
        IF in_trips + singles <> n_clean THEN
            RAISE EXCEPTION 'gap %: % points in trips + % singles <> % cleaned rows', g, in_trips, singles, n_clean;
        END IF;
    END LOOP;

    IF EXISTS (SELECT 1 FROM mobility.trips WHERE n_points < 2 OR start_ts >= end_ts) THEN
        RAISE EXCEPTION 'trip with fewer than 2 points or non-increasing time';
    END IF;
    IF EXISTS (SELECT 1 FROM mobility.trips WHERE numInstants(trip) <> n_points) THEN
        RAISE EXCEPTION 'tgeompoint instant count differs from n_points';
    END IF;
    RAISE NOTICE 'test_trips: all checks passed';
END $$;
