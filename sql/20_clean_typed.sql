-- 20_clean_typed.sql  (M2, step 0)
-- Copy every staging row into clean.ais with proper data types.
-- Nothing is removed here; the cleaning rules (21-25) each delete from clean.ais
-- and record how many rows they removed in clean.cleaning_log.
--
-- * row_hash: MD5 of all 26 original text columns, used by rule 1 to find exact duplicates.
-- * Timestamps are parsed as dd/mm/yyyy hh24:mi:ss and treated as UTC (assumption:
--   the DMA files do not state a zone in each row; see docs/decisions.md).
-- * Placeholder words become NULL ('Unknown value', 'Undefined', 'Unknown'),
--   so "missing" has one representation from here on.
-- * Casting is safe: results/profile.md showed 0 non-numeric values in every numeric column.
-- * UNLOGGED: derived data that can always be rebuilt, so the write-ahead log is skipped.

DROP SCHEMA IF EXISTS clean CASCADE;
CREATE SCHEMA clean;

CREATE TABLE clean.cleaning_log (
    step          int PRIMARY KEY,
    rule          text NOT NULL,
    description   text NOT NULL,
    rows_before   bigint NOT NULL,
    rows_removed  bigint NOT NULL,
    rows_after    bigint GENERATED ALWAYS AS (rows_before - rows_removed) STORED,
    logged_at     timestamptz NOT NULL DEFAULT now()
);

CREATE UNLOGGED TABLE clean.ais AS
SELECT
    s.row_id,
    md5(ROW(s.ts, s.type_of_mobile, s.mmsi, s.latitude, s.longitude, s.nav_status, s.rot,
            s.sog, s.cog, s.heading, s.imo, s.callsign, s.name, s.ship_type, s.cargo_type,
            s.width, s.length, s.pos_fixing_device, s.draught, s.destination, s.eta,
            s.data_source_type, s.dim_a, s.dim_b, s.dim_c, s.dim_d)::text)      AS row_hash,
    to_timestamp(s.ts, 'DD/MM/YYYY HH24:MI:SS')::timestamp                     AS ts_utc,
    s.type_of_mobile,
    s.mmsi::bigint                                                             AS mmsi,
    s.latitude::double precision                                               AS lat,
    s.longitude::double precision                                              AS lon,
    s.sog::real                                                                AS sog,
    s.cog::real                                                                AS cog,
    s.heading::real                                                            AS heading,
    s.rot::real                                                                AS rot,
    nullif(s.nav_status, 'Unknown value')                                      AS nav_status,
    nullif(s.ship_type, 'Undefined')                                           AS ship_type,
    s.name,
    nullif(s.imo, 'Unknown')                                                   AS imo,
    nullif(s.callsign, 'Unknown')                                              AS callsign,
    s.length::real                                                             AS length_m,
    s.width::real                                                              AS width_m,
    s.draught::real                                                            AS draught_m,
    nullif(s.destination, 'Unknown')                                           AS destination
FROM staging.ais_raw s;

ALTER TABLE clean.ais ADD PRIMARY KEY (row_id);
ANALYZE clean.ais;

INSERT INTO clean.cleaning_log (step, rule, description, rows_before, rows_removed)
SELECT 0, 'typed_copy', 'All staging rows copied with typed columns; nothing removed',
       count(*), 0
FROM clean.ais;
