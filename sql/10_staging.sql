-- 10_staging.sql
-- Load the raw DMA AIS CSV into a staging table, exactly as delivered.
-- Run through `make load`, which streams the CSV from the host into psql:
--     psql -f /sql/10_staging.sql < data/aisdk-2026-10-26.csv
--
-- Design decisions:
-- * Every column is TEXT. Nothing is converted or rejected at load time, so
--   bad values (a speed of 'abc', a latitude of 91) survive into staging,
--   where profiling can count them. Converting here would hide them.
-- * UNLOGGED: PostgreSQL skips the write-ahead log, which makes the load much
--   faster. The trade-off is that the table is emptied after a crash; that is
--   acceptable because it can always be rebuilt from the pinned file.
-- * row_id: the CSV line order, so any row can be traced back to the file.
-- * Client-side \copy from pstdin: the CSV is streamed from the host over the
--   normal database connection. Server-side COPY reading the file through the
--   Docker Desktop folder share (/data) crashed the Docker engine twice on a
--   2.86 GB file on Windows, so the share is avoided for bulk loads.

\timing on

CREATE SCHEMA IF NOT EXISTS staging;

DROP TABLE IF EXISTS staging.ais_raw;

CREATE UNLOGGED TABLE staging.ais_raw (
    row_id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ts                  text,  -- "# Timestamp", format dd/mm/yyyy hh24:mi:ss
    type_of_mobile      text,
    mmsi                text,
    latitude            text,
    longitude           text,
    nav_status          text,  -- "Navigational status"
    rot                 text,  -- rate of turn
    sog                 text,  -- speed over ground, knots
    cog                 text,  -- course over ground, degrees
    heading             text,
    imo                 text,
    callsign            text,
    name                text,
    ship_type           text,
    cargo_type          text,
    width               text,
    length              text,
    pos_fixing_device   text,  -- "Type of position fixing device"
    draught             text,
    destination         text,
    eta                 text,
    data_source_type    text,
    dim_a               text,  -- "A": GPS antenna to bow, metres
    dim_b               text,  -- "B": antenna to stern
    dim_c               text,  -- "C": antenna to port
    dim_d               text   -- "D": antenna to starboard
);

-- \copy must be written on one line (a psql meta-command ends at the newline).
-- pstdin = psql's own standard input, i.e. the file redirected with "<".
\copy staging.ais_raw (ts, type_of_mobile, mmsi, latitude, longitude, nav_status, rot, sog, cog, heading, imo, callsign, name, ship_type, cargo_type, width, length, pos_fixing_device, draught, destination, eta, data_source_type, dim_a, dim_b, dim_c, dim_d) FROM pstdin WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')

-- Refresh planner statistics after a bulk load.
ANALYZE staging.ais_raw;

SELECT count(*) AS rows_loaded FROM staging.ais_raw;
