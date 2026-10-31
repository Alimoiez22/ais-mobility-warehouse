-- 40_star_schema.sql  (M4, logical schema)
-- A constellation of two fact tables sharing conformed dimensions.
--
-- GRAIN
--   dw.fact_position : one row per cleaned AIS position report = one ship at one second.
--   dw.fact_trip     : one row per trip = one ship's continuous movement, split where
--                      consecutive reports are more than :trip_gap minutes apart (M3).
--
-- DIMENSIONS
--   dw.dim_ship        one row per vessel (MMSI) with its most frequently reported attributes
--   dw.dim_time        one row per hour of the day (the data covers one day)
--   dw.dim_cell        a 0.25 x 0.25 degree grid over the study area (53-59 N, 2-17 E)
--   dw.dim_nav_status  the navigational status the ship reported ('Unknown' if missing)
--
-- All tables are UNLOGGED: they are derived and can be rebuilt with `make star`.
-- Foreign keys are added after loading (41_star_etl.sql); adding them validates that
-- there are no orphan keys.

DROP SCHEMA IF EXISTS dw CASCADE;
CREATE SCHEMA dw;

CREATE UNLOGGED TABLE dw.dim_ship (
    ship_key      int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    mmsi          bigint NOT NULL UNIQUE,
    name          text,
    imo           text,
    callsign      text,
    ship_type     text NOT NULL,          -- 'Unknown' when never reported
    transponder   text NOT NULL,          -- 'Class A' or 'Class B'
    length_m      real,
    width_m       real
);

CREATE UNLOGGED TABLE dw.dim_time (
    time_key      int PRIMARY KEY,        -- yyyymmddhh, e.g. 2026102608
    day           date NOT NULL,
    hour          smallint NOT NULL CHECK (hour BETWEEN 0 AND 23),
    day_part      text NOT NULL           -- night 0-5, morning 6-11, afternoon 12-17, evening 18-23
);

CREATE UNLOGGED TABLE dw.dim_cell (
    cell_key      int PRIMARY KEY,        -- row * 1000 + col
    cell_row      smallint NOT NULL,
    cell_col      smallint NOT NULL,
    lat_min       double precision NOT NULL,
    lon_min       double precision NOT NULL,
    geom          geometry(Polygon, 4326) NOT NULL
);

CREATE UNLOGGED TABLE dw.dim_nav_status (
    nav_key       int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nav_status    text NOT NULL UNIQUE
);

CREATE UNLOGGED TABLE dw.fact_position (
    position_id   bigint PRIMARY KEY,     -- = staging row_id, traceable to the CSV line
    ship_key      int NOT NULL,
    time_key      int NOT NULL,
    cell_key      int NOT NULL,
    nav_key       int NOT NULL,
    ts            timestamptz NOT NULL,
    geom          geometry(Point, 4326) NOT NULL,
    sog_kn        real,                   -- measures
    cog_deg       real,
    heading_deg   real
);

CREATE UNLOGGED TABLE dw.fact_trip (
    trip_key        int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    gap_minutes     int NOT NULL,
    ship_key        int NOT NULL,
    start_time_key  int NOT NULL,
    end_time_key    int NOT NULL,
    start_cell_key  int NOT NULL,
    end_cell_key    int NOT NULL,
    start_ts        timestamptz NOT NULL,
    end_ts          timestamptz NOT NULL,
    n_points        int NOT NULL,         -- measures
    duration_min    double precision NOT NULL,
    length_km       double precision NOT NULL,
    avg_speed_kn    double precision,     -- NULL if duration is 0
    trip            tgeompoint NOT NULL,
    traj            geometry NOT NULL     -- the path as a line (or point if the ship did not move)
);
