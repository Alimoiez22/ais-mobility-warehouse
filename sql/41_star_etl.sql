-- 41_star_etl.sql  (M4, ETL into the star schema). Run with -v trip_gap=30.

-- Grid cell of a position: 0.25 degree steps from (53 N, 2 E); clamp the far edge
-- (latitude exactly 59 or longitude exactly 17) into the last cell.
CREATE OR REPLACE FUNCTION dw.cell_key(lat double precision, lon double precision)
RETURNS int LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT least(floor((lat - 53) / 0.25)::int, 23) * 1000 + least(floor((lon - 2) / 0.25)::int, 59)
$$;

-- dim_time: the 24 hours of the study day
INSERT INTO dw.dim_time (time_key, day, hour, day_part)
SELECT to_char(h, 'YYYYMMDDHH24')::int, h::date, extract(hour FROM h)::smallint,
       CASE WHEN extract(hour FROM h) < 6 THEN 'night'
            WHEN extract(hour FROM h) < 12 THEN 'morning'
            WHEN extract(hour FROM h) < 18 THEN 'afternoon'
            ELSE 'evening' END
FROM generate_series(timestamp '2026-10-26 00:00', timestamp '2026-10-26 23:00', interval '1 hour') AS h;

-- dim_cell: 24 rows x 60 columns of 0.25 degree cells
INSERT INTO dw.dim_cell (cell_key, cell_row, cell_col, lat_min, lon_min, geom)
SELECT r * 1000 + c, r, c, 53 + r * 0.25, 2 + c * 0.25,
       ST_MakeEnvelope(2 + c * 0.25, 53 + r * 0.25, 2 + (c + 1) * 0.25, 53 + (r + 1) * 0.25, 4326)
FROM generate_series(0, 23) AS r, generate_series(0, 59) AS c;

-- dim_nav_status
INSERT INTO dw.dim_nav_status (nav_status)
SELECT DISTINCT coalesce(nav_status, 'Unknown') FROM clean.ais ORDER BY 1;

-- dim_ship: one row per MMSI. Static fields are repeated in every report and can vary,
-- so each attribute takes its most frequent non-missing value (mode) over the day.
INSERT INTO dw.dim_ship (mmsi, name, imo, callsign, ship_type, transponder, length_m, width_m)
SELECT mmsi,
       mode() WITHIN GROUP (ORDER BY name)      FILTER (WHERE name IS NOT NULL),
       mode() WITHIN GROUP (ORDER BY imo)       FILTER (WHERE imo IS NOT NULL),
       mode() WITHIN GROUP (ORDER BY callsign)  FILTER (WHERE callsign IS NOT NULL),
       coalesce(mode() WITHIN GROUP (ORDER BY ship_type) FILTER (WHERE ship_type IS NOT NULL), 'Unknown'),
       mode() WITHIN GROUP (ORDER BY type_of_mobile),
       mode() WITHIN GROUP (ORDER BY length_m)  FILTER (WHERE length_m IS NOT NULL),
       mode() WITHIN GROUP (ORDER BY width_m)   FILTER (WHERE width_m IS NOT NULL)
FROM clean.ais
GROUP BY mmsi;

-- fact_position: every cleaned report
INSERT INTO dw.fact_position (position_id, ship_key, time_key, cell_key, nav_key, ts, geom,
                              sog_kn, cog_deg, heading_deg)
SELECT a.row_id, s.ship_key,
       to_char(a.ts_utc, 'YYYYMMDDHH24')::int,
       dw.cell_key(a.lat, a.lon),
       n.nav_key,
       a.ts_utc AT TIME ZONE 'UTC',
       ST_SetSRID(ST_MakePoint(a.lon, a.lat), 4326),
       a.sog, a.cog, a.heading
FROM clean.ais a
JOIN dw.dim_ship s ON s.mmsi = a.mmsi
JOIN dw.dim_nav_status n ON n.nav_status = coalesce(a.nav_status, 'Unknown');

-- fact_trip: trips built with the chosen gap value
INSERT INTO dw.fact_trip (gap_minutes, ship_key, start_time_key, end_time_key, start_cell_key,
                          end_cell_key, start_ts, end_ts, n_points, duration_min, length_km,
                          avg_speed_kn, trip, traj)
SELECT t.gap_minutes, s.ship_key,
       to_char(t.start_ts AT TIME ZONE 'UTC', 'YYYYMMDDHH24')::int,
       to_char(t.end_ts AT TIME ZONE 'UTC', 'YYYYMMDDHH24')::int,
       dw.cell_key(ST_Y(startValue(t.trip)), ST_X(startValue(t.trip))),
       dw.cell_key(ST_Y(endValue(t.trip)), ST_X(endValue(t.trip))),
       t.start_ts, t.end_ts, t.n_points,
       m.duration_s / 60.0,
       m.length_m / 1000.0,
       CASE WHEN m.duration_s > 0 THEN m.length_m / m.duration_s * 1.943844 END,  -- m/s to knots
       t.trip,
       trajectory(t.trip)
FROM mobility.trips t
JOIN dw.dim_ship s ON s.mmsi = t.mmsi
CROSS JOIN LATERAL (
    SELECT extract(epoch FROM t.end_ts - t.start_ts) AS duration_s,
           length(transform(t.trip, 25832))         AS length_m
) m
WHERE t.gap_minutes = :trip_gap;

-- Referential integrity: adding the foreign keys fails if any fact row has an orphan key.
ALTER TABLE dw.fact_position
    ADD FOREIGN KEY (ship_key) REFERENCES dw.dim_ship,
    ADD FOREIGN KEY (time_key) REFERENCES dw.dim_time,
    ADD FOREIGN KEY (cell_key) REFERENCES dw.dim_cell,
    ADD FOREIGN KEY (nav_key)  REFERENCES dw.dim_nav_status;
ALTER TABLE dw.fact_trip
    ADD FOREIGN KEY (ship_key)       REFERENCES dw.dim_ship,
    ADD FOREIGN KEY (start_time_key) REFERENCES dw.dim_time,
    ADD FOREIGN KEY (end_time_key)   REFERENCES dw.dim_time,
    ADD FOREIGN KEY (start_cell_key) REFERENCES dw.dim_cell,
    ADD FOREIGN KEY (end_cell_key)   REFERENCES dw.dim_cell;

-- Ordinary B-tree indexes for joins and time filters. The spatial index on
-- fact_position.geom is deliberately NOT created here: the benchmark (M6) creates
-- and compares none / GiST / SP-GiST itself.
CREATE INDEX ON dw.fact_position (ship_key);
CREATE INDEX ON dw.fact_position (time_key);
CREATE INDEX ON dw.fact_position (ts);
CREATE INDEX ON dw.fact_trip (ship_key);
CREATE INDEX ON dw.fact_trip (start_ts, end_ts);

ANALYZE dw.dim_ship; ANALYZE dw.dim_time; ANALYZE dw.dim_cell; ANALYZE dw.dim_nav_status;
ANALYZE dw.fact_position; ANALYZE dw.fact_trip;
