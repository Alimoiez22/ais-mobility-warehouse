# Every step of the project is one `make` target, so the whole pipeline
# can be reproduced with `make all`. Targets are added milestone by milestone.

# Read POSTGRES_USER and POSTGRES_DB from .env (copy .env.example first).
-include .env

# Which day of AIS data to use. Override with: make download AIS_DATE=2026-10-27
AIS_DATE ?= 2026-10-26

PSQL = docker compose exec -T db psql -v ON_ERROR_STOP=1 -U $(POSTGRES_USER) -d $(POSTGRES_DB)

.PHONY: all up init download status psql logs down destroy

## all: run the full pipeline (grows with each milestone)
all: init download

## up: start the database and wait until it is healthy
up:
	docker compose up -d --wait

## init: start the database and create the PostGIS and MobilityDB extensions
init: up
	$(PSQL) -f /sql/00_extensions.sql

## download: fetch one day of AIS data, verify its checksum, unzip into data/
download:
	uv run python scripts/download.py --date $(AIS_DATE)

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
