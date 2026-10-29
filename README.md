# AIS Mobility Data Warehouse

> Status: work in progress (milestone M0: database environment). Nothing below is a result yet.

A reproducible data warehouse built on one day of real ship-tracking (AIS) data from the Danish Maritime Authority, using PostgreSQL, PostGIS and MobilityDB in Docker.

## Research questions
- **RQ1:** What data-quality problems exist in raw AIS data, and how many rows does each cleaning rule remove?
- **RQ2:** Can a multidimensional model answer realistic maritime questions with OLAP queries?
- **RQ3:** How much do spatiotemporal indexes (none vs GiST vs SP-GiST) change query latency?

## Repository layout
| Folder | Contents |
|---|---|
| `sql/` | Numbered SQL files, run in order |
| `scripts/` | Python scripts (download, profiling) |
| `benchmarks/` | Index benchmark runner |
| `tests/` | Row-count and integrity tests |
| `results/` | Generated outputs (profile, cleaning counts, timings) |
| `docs/` | Decision records, report, figures |
| `data/` | Raw data, downloaded locally, never committed |

## How to reproduce
Requirements: Docker (with Compose), GNU Make, Git, uv.

**Windows note:** with Docker Desktop's default settings, loading the 2.86 GB CSV restarted Docker's WSL2 virtual machine four times on a 16 GB laptop (the VM was stopped from the Windows side; nothing was logged inside it). Capping the VM fixed it. Put this in `%UserProfile%\.wslconfig`, then run `wsl --shutdown` and restart Docker Desktop:

```ini
[wsl2]
memory=4GB
swap=8GB

[experimental]
autoMemoryReclaim=dropCache
```

```bash
cp .env.example .env    # PowerShell: Copy-Item .env.example .env
make all                # database + extensions, download the day, load it into staging
make status             # shows the container and extension versions
```

Other targets: `make psql` (SQL prompt), `make logs`, `make down` (stop, keep data), `make destroy` (stop and delete data).

The database image is pinned by digest in `docker-compose.yml`, so every run uses the same PostgreSQL, PostGIS and MobilityDB versions.

## Plan
See [PLAN.md](PLAN.md).

## Data source and attribution
Contains data from the Danish Maritime Authority that is used in accordance with the conditions for the use of Danish public data.

Raw data is not redistributed in this repository. `make download` fetches it and verifies it against the SHA-256 checksum pinned in [`data.lock.json`](data.lock.json).

| Day used | Zip | Uncompressed CSV | Columns | Rows loaded into staging |
|---|---|---|---|---|
| 26 Oct 2026 (`aisdk-2026-10-26.zip`) | 567.5 MB | 2.86 GB | 26 | 15,808,081 (3.8 GB table) |

The day was chosen as the newest full day available on 29 Oct 2026. It is a normal 24-hour day (the Danish daylight-saving change was on 25 Oct). The zip was fetched with a resumable multi-connection downloader because the connection was slow, so the lock file has no server `Last-Modified` value; the checksum identifies the file exactly.

## AI-use note
AI assistance (Claude) was used for planning, explanations and review. The author chose the cleaning rules, designed the conceptual schema, wrote the business questions, interpreted the results and wrote the report.

## Licence
Code: MIT (see [LICENSE](LICENSE)). The DMA data is subject to its own conditions.
