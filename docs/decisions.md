# Decision log

Every project decision, with its reason and evidence.
**Status** says who made it: *proposed by Claude* means the AI assistant suggested it to get
the pipeline running end to end; the author must review it and then mark it *accepted* or
*changed* (and edit the file and rerun the step if changed). Reasons for accepted decisions
are rewritten by the author in his own words.

| # | Date | Decision | Reason | Evidence | Alternatives considered | Status |
|---|---|---|---|---|---|---|
| 1 | 2026-10-29 | Use one day of DMA AIS data: 26 Oct 2026 | Newest full day available; a normal 24-hour day (daylight-saving change was 25 Oct) | `data.lock.json` | A sample of the first N rows; several days | author to write reason |
| 2 | 2026-10-30 | Cap Docker's WSL VM at 4 GB memory, 8 GB swap | The uncapped VM was stopped by Windows four times during the 2.86 GB load | README Windows note; Docker Desktop logs | Smaller load batches; loading over TCP | author to write reason |
| 3 | 2026-10-31 | Load every column as TEXT into staging first | Bad values must survive to be counted by profiling | `sql/10_staging.sql` | Typed columns at load time | proposed by Claude |
| 4 | 2026-10-31 | Treat timestamps as UTC | DMA files do not state a zone per row; UTC is assumed, not yet confirmed | `sql/20_clean_typed.sql` | Local Danish time | proposed by Claude, **verify against the DMA field note** |
| 5 | 2026-10-31 | Cleaning rule 1: remove exact duplicates (keep first) | 38.4% of rows are exact copies; copies add no information | `results/profile.md` section 6 | Keep duplicates and dedupe in queries | proposed by Claude |
| 6 | 2026-10-31 | Cleaning rule 2: keep only Class A and Class B | The warehouse models vessels; base stations and buoys do not move, aircraft are not vessels | profile section 1 | Keep AtoN as a separate dimension | proposed by Claude |
| 7 | 2026-10-31 | Cleaning rule 3: keep MMSI 200000000-799999999 | The MMSI is the ship key; malformed IDs cannot be linked to one vessel | profile section 5 | Keep all and flag | proposed by Claude |
| 8 | 2026-10-31 | Cleaning rule 4: keep 53-59 N, 2-17 E | Removes latitude 91 (not available) and impossible far-away positions | profile section 3 | Tighter box; a polygon of Danish waters | proposed by Claude |
| 9 | 2026-10-31 | Cleaning rule 5: one report per ship per second | Trajectories need strictly increasing timestamps | profile section 6 | Average conflicting positions | proposed by Claude |
| 10 | 2026-10-31 | Rule order: 1, 2, 3, 4, 5 | Pure redundancy first, then scope, identity, position, then conflicts | `results/cleaning.csv` | Other orders change the per-rule counts | proposed by Claude |
| 11 | 2026-10-31 | Speeds over 102.2 kn are not a cleaning rule | A bad reported speed does not make the position wrong; implausible movement is flagged in M3 instead | profile section 3; `results/trips_compare.csv` | Remove those rows | proposed by Claude |
| 12 | 2026-10-31 | Compare trip gaps of 10 and 30 minutes; use 30 in the warehouse | 30 min tolerates short reception gaps without merging separate voyages | `results/trips_compare.csv` | 5, 60 minutes | proposed by Claude, **author to choose after reading the comparison** |
| 13 | 2026-10-31 | Two fact tables: position (ship x second) and trip | Positions answer traffic and density questions and drive the index benchmark; trips answer voyage questions | `sql/40_star_schema.sql` | One position-level fact only | proposed by Claude, **author to redraw in MultiDim notation** |
| 14 | 2026-10-31 | Spatial dimension = 0.25-degree grid | No external sea-area boundaries are needed, so the project stays reproducible from one file | `sql/41_star_etl.sql` | HELCOM sub-basins; H3 cells | proposed by Claude |
| 15 | 2026-10-31 | Ship attributes = most frequent value over the day | Static AIS fields vary between reports of the same ship | `sql/41_star_etl.sql` | First or last value; slowly changing dimension | proposed by Claude |
| 16 | 2026-10-31 | 8 business questions in `sql/olap/` | Cover ROLLUP, CUBE, spatial window, temporal window and proximity as the plan requires | `results/olap_runtimes.csv` | | proposed by Claude, **author to rewrite or replace** |
| 17 | 2026-10-31 | Benchmark: 3 queries x {none, GiST, SP-GiST}, 2 warm-ups + 5 runs, median and IQR, warm cache only | Median and IQR resist outliers; cold cache cannot be forced reliably inside Docker on Windows | `benchmarks/run.py` | Mean and standard deviation; cold runs after container restart | proposed by Claude |
