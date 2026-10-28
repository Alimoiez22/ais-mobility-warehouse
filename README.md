# AIS Mobility Data Warehouse

> Status: work in progress (milestone M0, repository skeleton). Nothing below is a result yet.

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
Coming at milestone M0: `docker compose up` followed by `make all`.

## Plan
See [PLAN.md](PLAN.md).

## Data source and attribution
Contains data from the Danish Maritime Authority that is used in accordance with the conditions for the use of Danish public data.

Raw data is not redistributed in this repository. It is downloaded by a script and verified with a checksum.

## AI-use note
AI assistance (Claude) was used for planning, explanations and review. The author chose the cleaning rules, designed the conceptual schema, wrote the business questions, interpreted the results and wrote the report.

## Licence
Code: MIT (see [LICENSE](LICENSE)). The DMA data is subject to its own conditions.
