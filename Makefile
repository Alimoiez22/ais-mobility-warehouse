# Every step of the project is one `make` target; `make all` runs the whole pipeline.
#   make all    database + extensions, download, load, profile, clean, trips, star schema,
#               OLAP queries, index benchmark, figures, summary
# Individual steps can be rerun on their own, e.g. `make clean` or `make bench`.

# Read POSTGRES_USER and POSTGRES_DB from .env (copy .env.example first).
-include .env

# Which day of AIS data to use. Override with: make download AIS_DATE=2026-10-27
AIS_DATE ?= 2026-10-26
# Trip split thresholds compared in M3 (minutes), and the one used in the warehouse.
GAP_A ?= 10
GAP_B ?= 30
TRIP_GAP ?= 30

PSQL = docker compose exec -T db psql -v ON_ERROR_STOP=1 -U $(POSTGRES_USER) -d $(POSTGRES_DB)
PSQLQ = $(PSQL) -q

.PHONY: all up init download load profile clean trips star olap bench figures summary test status psql logs down destroy

## all: run the full pipeline from the raw file to the figures
all: init download load profile clean trips star olap bench figures summary

## up: start the database and wait until it is healthy
up:
	docker compose up -d --wait

## init: start the database and create the PostGIS and MobilityDB extensions
init: up
	$(PSQL) -f /sql/00_extensions.sql

## download: fetch one day of AIS data, verify its checksum, unzip into data/
download:
	uv run python scripts/download.py --date $(AIS_DATE)

## load: copy the raw CSV into staging.ais_raw (all TEXT) and record the row count
load:
	$(PSQL) -f /sql/10_staging.sql < data/aisdk-$(AIS_DATE).csv
	$(PSQL) -A -F , -P footer=off -c "SELECT 'aisdk-$(AIS_DATE).csv' AS source_file, count(*) AS rows_loaded, pg_size_pretty(pg_total_relation_size('staging.ais_raw')) AS table_size FROM staging.ais_raw;" > results/staging_rowcount.csv

## profile: measure data-quality problems in staging, write results/profile.md
profile:
	uv run python scripts/profile.py

## clean: M2, apply the cleaning rules in order, test them, write results/cleaning.csv
clean:
	$(PSQLQ) -f /sql/20_clean_typed.sql
	$(PSQLQ) -f /sql/21_rule_exact_duplicates.sql
	$(PSQLQ) -f /sql/22_rule_non_vessel.sql
	$(PSQLQ) -f /sql/23_rule_invalid_mmsi.sql
	$(PSQLQ) -f /sql/24_rule_outside_area.sql
	$(PSQLQ) -f /sql/25_rule_same_ship_same_second.sql
	$(PSQLQ) -f /sql/tests/test_clean.sql
	$(PSQLQ) --csv -f /sql/29_cleaning_report.sql > results/cleaning.csv

## trips: M3, build MobilityDB trips for two gap values, compare them, test them
trips:
	$(PSQLQ) -f /sql/30_mobilitydb_check.sql
	$(PSQLQ) -v gap=$(GAP_A) -f /sql/31_trips.sql
	$(PSQLQ) -v gap=$(GAP_B) -f /sql/31_trips.sql
	$(PSQLQ) -f /sql/tests/test_trips.sql
	$(PSQLQ) --csv -f /sql/32_trips_compare.sql > results/trips_compare.csv

## star: M4, build the star schema and load it, test integrity, write row counts
star:
	$(PSQLQ) -f /sql/40_star_schema.sql
	$(PSQLQ) -v trip_gap=$(TRIP_GAP) -f /sql/41_star_etl.sql
	$(PSQLQ) -v trip_gap=$(TRIP_GAP) -f /sql/tests/test_star.sql
	$(PSQLQ) --csv -f /sql/42_star_counts.sql > results/star_counts.csv

## olap: M5, run the 8 business questions, save results and runtimes
olap:
	uv run python scripts/run_olap.py

## bench: M6, compare no index vs GiST vs SP-GiST (5 runs each, EXPLAIN plans saved)
bench:
	uv run python benchmarks/run.py

## figures: regenerate every figure from the result files
figures:
	uv run python benchmarks/plot.py

## summary: collect all headline numbers into results/summary.md
summary:
	uv run python scripts/summary.py

## test: rerun all data tests against the current database
test:
	$(PSQLQ) -f /sql/tests/test_clean.sql
	$(PSQLQ) -f /sql/tests/test_trips.sql
	$(PSQLQ) -v trip_gap=$(TRIP_GAP) -f /sql/tests/test_star.sql

## status: show the container state and the installed extension versions
status:
	docker compose ps
	$(PSQL) -c "SELECT extname, extversion FROM pg_extension ORDER BY extname;"

## psql: open an interactive SQL prompt (type \q to leave)
psql:
	docker compose exec db psql -U $(POSTGRES_USER) -d $(POSTGRES_DB)

## logs: last 50 lines of the database log
logs:
	docker compose logs --tail=50 db

## down: stop the database; the data is kept
down:
	docker compose down

## destroy: stop the database AND delete all its data (asks no questions)
destroy:
	docker compose down -v
