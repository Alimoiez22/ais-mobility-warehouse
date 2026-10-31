-- 31_trips.sql  (M3)
-- Turn each ship's cleaned positions into trips, split wherever two consecutive reports
-- of the same ship are more than :gap minutes apart. Run once per gap value:
--     psql -v gap=30 -f /sql/31_trips.sql
--
-- A trip is stored as one MobilityDB tgeompoint: a moving point, i.e. a sequence of
-- (position, time) instants with linear interpolation between them.
-- Trips with a single report are not trajectories (nothing moves) and are not stored;
-- 32_trips_compare.sql counts them separately.

CREATE SCHEMA IF NOT EXISTS mobility;

CREATE UNLOGGED TABLE IF NOT EXISTS mobility.trips (
    gap_minutes  int         NOT NULL,
    mmsi         bigint      NOT NULL,
    trip_no      int         NOT NULL,
    start_ts     timestamptz NOT NULL,
    end_ts       timestamptz NOT NULL,
    n_points     int         NOT NULL,
    trip         tgeompoint  NOT NULL,
    PRIMARY KEY (gap_minutes, mmsi, trip_no)
);

CREATE UNLOGGED TABLE IF NOT EXISTS mobility.trip_segments (
    gap_minutes  int    PRIMARY KEY,
    segments     bigint NOT NULL,   -- all pieces, including single-report pieces
    single_point bigint NOT NULL    -- pieces with one report (not stored as trips)
);

DELETE FROM mobility.trips WHERE gap_minutes = :gap;
DELETE FROM mobility.trip_segments WHERE gap_minutes = :gap;

CREATE TEMP TABLE numbered AS
WITH p AS (
    SELECT mmsi, ts_utc, lon, lat,
           CASE WHEN lag(ts_utc) OVER w IS NULL
                  OR ts_utc - lag(ts_utc) OVER w > make_interval(mins => :gap)
                THEN 1 ELSE 0 END AS starts_trip
    FROM clean.ais
    WINDOW w AS (PARTITION BY mmsi ORDER BY ts_utc)
)
SELECT mmsi, ts_utc, lon, lat,
       sum(starts_trip) OVER (PARTITION BY mmsi ORDER BY ts_utc ROWS UNBOUNDED PRECEDING)::int AS trip_no
FROM p;

INSERT INTO mobility.trip_segments (gap_minutes, segments, single_point)
SELECT :gap, count(*), count(*) FILTER (WHERE n = 1)
FROM (SELECT count(*) AS n FROM numbered GROUP BY mmsi, trip_no) s;

INSERT INTO mobility.trips (gap_minutes, mmsi, trip_no, start_ts, end_ts, n_points, trip)
SELECT :gap,
       mmsi,
       trip_no,
       min(ts_utc) AT TIME ZONE 'UTC',
       max(ts_utc) AT TIME ZONE 'UTC',
       count(*),
       tgeompointSeq(array_agg(
           tgeompoint(ST_SetSRID(ST_MakePoint(lon, lat), 4326), ts_utc AT TIME ZONE 'UTC')
           ORDER BY ts_utc))
FROM numbered
GROUP BY mmsi, trip_no
HAVING count(*) >= 2;

DROP TABLE numbered;
ANALYZE mobility.trips;
