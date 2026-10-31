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
    -- MobilityDB normalises a sequence: an instant that lies exactly on the straight line
    -- between its neighbours (e.g. a moored ship repeating the same position) adds no
    -- information under linear interpolation and is dropped. So the stored instant count
    -- may be smaller than n_points, but never larger, and a trip keeps at least 2.
    IF EXISTS (SELECT 1 FROM mobility.trips WHERE numInstants(trip) > n_points OR numInstants(trip) < 2) THEN
        RAISE EXCEPTION 'tgeompoint has more instants than reports, or fewer than 2';
    END IF;
    RAISE NOTICE 'test_trips: all checks passed';
END $$;
