-- 00_extensions.sql
-- Enables the spatial (PostGIS) and moving-object (MobilityDB) types.
-- CASCADE also installs PostGIS, which MobilityDB depends on.
-- IF NOT EXISTS makes the file safe to run more than once.
CREATE EXTENSION IF NOT EXISTS mobilitydb CASCADE;
