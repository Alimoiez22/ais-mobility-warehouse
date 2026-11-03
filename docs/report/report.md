# AIS Mobility Data Warehouse: data quality, multidimensional modelling and spatial indexing on one day of Danish ship traffic

**Author:** Ali Moiez · **Version:** 1.0 (November 2026) · **Code and data pipeline:** <https://github.com/Alimoiez22/ais-mobility-warehouse> · **Dashboard:** <https://alimoiez22.github.io/ais-mobility-warehouse/>

## Abstract

Ships broadcast their position several times a minute through the Automatic Identification System (AIS). Public AIS archives are a rich source for maritime analytics, but the raw files are large and noisy. This project builds a reproducible warehouse on one full day of AIS data from the Danish Maritime Authority (26 October 2026, 15,808,081 reports) using PostgreSQL 18, PostGIS 3.6 and MobilityDB 1.3 in Docker. Three questions are studied. **RQ1:** six logged cleaning rules removed 42.1% of the raw reports; exact duplicates alone account for 38.4%. **RQ2:** a star schema with two fact tables (9,145,393 positions, 4,488 trips) and four dimensions answers eight analytical questions, including ROLLUP, CUBE, spatio-temporal windows and ship-to-ship proximity. **RQ3:** a GiST index alone sped up a small spatial window query only 2.0×, because the matching rows were scattered across 31% of the table's pages; the same index on a spatially sorted copy read 45× fewer pages and ran 102× faster than a full scan. Every number is regenerated from the raw file by one command (`make all`).

## 1. Introduction

AIS was designed for collision avoidance, not analytics. Messages are received by many base stations and satellites, so the same report can arrive several times; transmitters include buoys, base stations and aircraft as well as ships; and positions can be wrong. Before AIS data can answer questions such as "where is traffic densest?" or "which ships came close to each other?", it needs cleaning, a model that fits analytical queries, and storage that keeps spatial queries fast.

This project treats those three needs as research questions:

- **RQ1.** What data-quality problems exist in raw AIS data, and how many rows does each cleaning rule remove?
- **RQ2.** Can a multidimensional model, following the MultiDim approach of Vaisman and Zimányi, answer realistic maritime questions with OLAP queries?
- **RQ3.** How much do spatial indexes (none, GiST, SP-GiST) change query latency, and why?

Streaming, machine learning and cloud services are out of scope.

## 2. Data

The source is the Danish Maritime Authority (DMA) historical AIS archive, one CSV per day. The file used is `aisdk-2026-10-26` (zip 567.5 MB, CSV 2.86 GB, 26 columns), the newest complete day when the project started and a normal 24-hour day. Its SHA-256 checksum is pinned in `data.lock.json`, and the raw file is not redistributed. Timestamps are treated as UTC.

Profiling the raw table (`results/profile.md`) showed, before any cleaning:

- 3,218 distinct transmitter IDs (MMSI) of seven kinds. Class A ship transponders sent 88.5% of reports; base stations (6.1%), aids to navigation (1.6%) and search-and-rescue aircraft were also present.
- Missing values are common in voyage fields: IMO number missing in 42.8% of rows, ETA 38.2%, rate of turn 32.9%, draught 28.2%, destination 27.7%. Position and timestamp are never empty.
- 20,268 reports carry latitude 91, the AIS code for "not available"; 2,467 report speeds above the 102.2-knot maximum.

## 3. Method

### 3.1 Pipeline

Every step is a numbered SQL file or a small Python script, run by one Makefile target, inside a Docker container whose image is pinned by digest:

1. **Load** the CSV into a staging table with every column as text, so that bad values survive to be counted.
2. **Profile** the staging table.
3. **Clean**: copy into typed columns, then apply six rules in a fixed order. Each rule writes its row counts before and after into a cleaning log, and SQL tests stop the pipeline if the counts do not add up.
4. **Trips**: split each ship's ordered positions wherever reporting stops for more than a gap threshold, and store each piece as a MobilityDB `tgeompoint` sequence. Gaps of 10 and 30 minutes were compared.
5. **Star schema**: build dimensions and facts with foreign keys and integrity tests.
6. **OLAP**: run eight analytical queries and record their runtimes.
7. **Benchmark**: time three spatial queries under four physical designs.

### 3.2 Cleaning rules

| Step | Rule | Why |
|---|---|---|
| 1 | Remove rows identical in all 26 columns (keep the first) | copies add no information |
| 2 | Keep only Class A and Class B transponders | the warehouse models vessels |
| 3 | Keep MMSI 200000000–799999999 | the MMSI is the ship key; malformed IDs cannot be linked to one vessel |
| 4 | Keep positions in 53–59 N, 2–17 E | removes the latitude-91 code and impossible far-away positions |
| 5 | Keep one report per ship per second | trajectories need strictly increasing timestamps |
| 6 | Remove isolated position jumps: implied speed into **and** out of a report above 60 knots | a single wrong position creates two impossible speeds; requiring both keeps its correct neighbours |

Rule 6 was added after the first full run, when some cargo ships appeared to travel thousands of kilometres in a day.

### 3.3 Dimensional model

The conceptual model has two facts at different grains:

- **Position** (one ship at one second), with measures speed, course and heading. It serves traffic and density questions and the index benchmark.
- **Trip** (one ship's continuous movement until a gap of more than 30 minutes), with measures number of reports, duration, length and average speed. Its geometry is the trajectory.

They share four dimensions: **Ship** (MMSI, name, type, transponder class, size; static attributes take the most frequent value over the day), **Time** (hour, part of day), **Cell** (a regular 0.25° grid) and **Navigational status**. The grid was chosen over real sea-area boundaries so the project depends on a single source file.

### 3.4 Benchmark design

Three queries on `fact_position` (9.1 M rows): **B1** counts reports in a small window over Copenhagen harbour; **B2** counts reports in a large window over the Great Belt; **B3** finds the ten nearest reports to a point in the Øresund (`ORDER BY geom <-> point LIMIT 10`). Four setups: no index; GiST; SP-GiST; and GiST on a copy of the table physically sorted by location (geohash). Each query ran twice as a warm-up and five times measured. The median and interquartile range are reported, and `EXPLAIN (ANALYZE, BUFFERS)` plans are saved. Environment: Windows 11 laptop, Docker Desktop WSL2 VM with 8 CPUs and 4 GB memory, PostgreSQL 18.4 defaults (`shared_buffers` 128 MB, two parallel workers per query).

## 4. Results

### 4.1 RQ1: data quality

| Step | Rule | Removed | % of raw |
|---|---|---|---|
| 1 | Exact duplicates | 6,076,234 | 38.44% |
| 2 | Not a Class A/B ship transponder | 474,638 | 3.00% |
| 3 | Invalid ship MMSI | 39,377 | 0.25% |
| 4 | Outside the study area | 13,150 | 0.08% |
| 5 | Same ship, same second | 59,136 | 0.37% |
| 6 | Isolated position jumps | 153 | <0.01% |
| | **Total removed / kept** | **6,662,688 / 9,145,393** | **42.1% / 57.9%** |

The dominant problem is redundancy, not error: more than a third of the file consists of exact copies, most likely the same message received by more than one station. Scope problems (non-ship transmitters) come second. Genuinely wrong values are rare once duplicates are gone, but they matter far more than their count suggests: 153 jump points were enough to create trips that "travelled" thousands of kilometres. Rule 6 also has a known blind spot. A ship whose positions are offset for a long stretch produces only one impossible speed at each end of the stretch, so it is not caught. After cleaning, 5 of 4,488 trips still average more than 50 knots. The longest, by cargo ship BEUKBORG, covers 894 km in under eight hours (61.6 kn), which is impossible for that ship.

### 4.2 Trips: choosing the gap

| Gap | Trips | Single-report pieces | Median reports per trip | Median duration | Median length |
|---|---|---|---|---|---|
| 10 min | 10,170 | 4,182 | 10 | 27 min | 0.02 km |
| 30 min | 4,488 | 977 | 423 | 433 min | 0.77 km |

A 10-minute gap breaks voyages at ordinary reception gaps, producing many tiny fragments. A 30-minute gap keeps voyages whole while still separating them. The warehouse uses 30 minutes. Median trip lengths are short because many ships spend the day moored or at anchor, reporting small GPS movements.

### 4.3 RQ2: questions the warehouse answers

| # | Question | OLAP technique | Rows | Runtime |
|---|---|---|---|---|
| Q1 | Traffic by ship type and part of day | ROLLUP | 126 | 14.1 s |
| Q2 | Ship type × navigational status with all subtotals | CUBE | 133 | 20.1 s |
| Q3 | Grid cells with the most distinct ships | spatial aggregation | 10 | 7.0 s |
| Q4 | Ship types in the Øresund 07:00–09:00 | spatial + temporal window | 18 | 130 ms |
| Q5 | Trips under way between 12:00 and 13:00 | temporal window on trips | 25 | 10 ms |
| Q6 | Ship pairs within 500 m in the same minute (Øresund, 07:00–09:00) | proximity | 20 | 621 ms |
| Q7 | Trip length and speed per type and transponder class | ROLLUP on trips | 25 | 9 ms |
| Q8 | The ten longest trips | ranking | 10 | 11 ms |

All eight questions were answered with plain SQL against the star schema. Examples of what they show: cargo ships were the most common type (511 ships) but fishing vessels sent the most reports (2.4 million). The busiest cell is the Øresund off Copenhagen (172 distinct ships). The closest encounters in Q6 are Copenhagen harbour buses passing within 38 m of each other. The traffic level is almost flat through the day, between 2,190 and 2,329 ships reporting in every hour.

The two fact grains turned out to matter. Position-level questions (Q1–Q3) scan millions of rows and take seconds; trip-level questions (Q5, Q7, Q8) take milliseconds because one trip row summarises hundreds of reports. A model with only the position fact could answer the trip questions, but much more slowly and with more complex SQL.

### 4.4 RQ3: spatial indexes

| Query | No index | GiST | SP-GiST | GiST, sorted rows |
|---|---|---|---|---|
| B1 small window | 1,008 ms | 512 ms (2.0×) | 523 ms (1.9×) | **9.9 ms (102×)** |
| B2 large window | 979 ms | 1,099 ms (0.9×) | 1,086 ms (0.9×) | **72.7 ms (13.5×)** |
| B3 10 nearest | 2,568 ms | **0.57 ms (4,521×)** | 2,277 ms (1.1×) | 0.50 ms (5,115×) |

Medians of five runs; speed-up relative to no index. Data pages read (shared buffers, from the saved plans):

| Query | No index | GiST | SP-GiST | GiST, sorted rows |
|---|---|---|---|---|
| B1 | 121,939 | 38,127 | 39,170 | 841 |
| B2 | 121,939 | 101,801 | 106,298 | 3,912 |
| B3 | 122,015 | 47 | 122,015 | 37 |

The page counts explain the latencies. Positions were stored in time order, so the reports inside any small area were spread over the whole table. For B1, the index found the matching rows quickly, but fetching them still touched 31% of all pages, and for the large window B2 the index was slower than a full scan. Sorting the rows by location put neighbouring positions on the same pages: the same GiST index then read 45 times fewer pages for B1 and 26 times fewer for B2. The physical order of the data mattered more than the choice between GiST and SP-GiST, which behaved almost identically for window queries.

For nearest-neighbour search the picture is different. GiST supports ordered `<->` scans, so B3 read 47 pages and finished in half a millisecond. With SP-GiST the planner did not use the index for this query: it read the whole table and sorted it, so SP-GiST gave no benefit.

## 5. Threats to validity

- **One day, one provider.** Traffic patterns, error rates and duplicate shares may differ on other days, in other seasons and in other countries' data.
- **Warm cache only.** Cold-cache timings could not be forced reliably inside Docker on Windows, so the absolute numbers favour repeated queries. The page counts do not depend on caching and support the same conclusions.
- **One machine, default settings.** A 4 GB VM with `shared_buffers` of 128 MB; a tuned server would change absolute times.
- **Sorted copy.** The sorted table was built once for the benchmark. A production table receiving new data would need periodic re-sorting (for example `CLUSTER`) to keep the benefit.
- **Cleaning thresholds.** The 60-knot jump threshold and the 30-minute trip gap are judgement calls. They are documented in the decision log and parameterised in the Makefile (`MAX_KN`, `TRIP_GAP`).
- **UTC assumption.** If DMA timestamps were local time, the hourly figures would shift by one hour; no other result would change.

## 6. Conclusion

On one day of Danish AIS data, most of the cleaning effort is removing redundancy: 38.4% of reports are exact copies. Truly wrong positions are rare but distort trip-level results out of proportion to their number. A star schema with one fact table per grain answers a broad set of maritime questions with standard OLAP SQL, and the trip grain keeps voyage questions in the millisecond range, while position-level questions take seconds. For spatial queries, how the rows are physically laid out decides whether an index helps: GiST on time-ordered data was barely faster than no index, and GiST on location-ordered data was 102 times faster.

Next steps: detect sustained position offsets (for example by comparing reported and implied speed over a window), repeat the study over a week, and measure cold-cache behaviour on a Linux host.

## Reproducibility

```
git clone https://github.com/Alimoiez22/ais-mobility-warehouse.git
cd ais-mobility-warehouse
cp .env.example .env
make all
```

The image digest, source checksum and every parameter are pinned in the repository. The decision log (`docs/decisions.md`) records each design decision with its evidence.

## Acknowledgements and AI use

Data: Danish Maritime Authority; contains data used in accordance with the conditions for the use of Danish public data. Coastline in the dashboard: Natural Earth (public domain). Much of the code, and an early draft of this report, were written with an AI assistant (Claude) under the author's direction. The author ran and checked every step, and is responsible for the decisions and conclusions.

## References

- Vaisman, A. and Zimányi, E. (2022). *Data Warehouse Systems: Design and Implementation*, 2nd edition. Springer.
- Zimányi, E., Sakr, M. and Lesuisse, A. (2020). MobilityDB: A Mobility Database Based on PostgreSQL and PostGIS. *ACM Transactions on Database Systems* 45(4).
- ITU-R Recommendation M.1371: Technical characteristics for an automatic identification system using time division multiple access in the VHF maritime mobile frequency band.
- Danish Maritime Authority, historical AIS data: <https://web.ais.dk/aisdata/>
