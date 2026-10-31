"""RQ3 benchmark: how much do spatial indexes change query latency?

Usage: uv run python benchmarks/run.py [--runs 5] [--warmups 2]

Design
  Table    dw.fact_position (one row per cleaned position report), column geom (Point, 4326)
  Indexes  none  | GiST (R-tree over bounding boxes) | SP-GiST (space-partitioning quad-tree)
  Queries  B1 small window   positions in a ~2 km box near Copenhagen harbour
           B2 large window   positions in the Great Belt area (~25 x 55 km)
           B3 kNN            the 10 positions nearest to a point in the Øresund
  Protocol for each index configuration: drop all spatial indexes on geom, build the
           index (time and size recorded), VACUUM ANALYZE, then for each query run
           `warmups` unmeasured runs followed by `runs` measured runs of
           EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON). The reported latency is the server's
           "Execution Time". Shared-buffer hits and reads are recorded per run.
  Caching  WARM cache only: the warm-up runs load the pages into memory. A true cold
           cache would need the OS page cache inside Docker's VM to be dropped, which is
           not reliably possible from here; see the threats to validity.

Outputs (all regenerated on every run)
  results/bench/timings.csv      every measured run
  results/bench/summary.csv      median, Q1, Q3, IQR per configuration and query
  results/bench/indexes.csv      build time and size per index
  results/bench/plans/*.json     the last EXPLAIN plan per configuration and query
  results/bench/environment.txt  hardware and software the numbers were measured on
"""

from __future__ import annotations

import argparse
import csv
import json
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import dbutil  # noqa: E402

OUT = dbutil.REPO_ROOT / "results" / "bench"
TABLE = "dw.fact_position"

QUERIES = {
    "B1_small_window": f"""
        SELECT count(*) FROM {TABLE}
        WHERE geom && ST_MakeEnvelope(12.58, 55.68, 12.62, 55.70, 4326)""",
    "B2_large_window": f"""
        SELECT count(*) FROM {TABLE}
        WHERE geom && ST_MakeEnvelope(10.80, 55.10, 11.20, 55.60, 4326)""",
    "B3_knn_10": f"""
        SELECT position_id FROM {TABLE}
        ORDER BY geom <-> ST_SetSRID(ST_MakePoint(12.70, 55.90), 4326)
        LIMIT 10""",
}
CONFIGS = {
    "none": None,
    "gist": f"CREATE INDEX bench_geom_idx ON {TABLE} USING gist (geom)",
    "spgist": f"CREATE INDEX bench_geom_idx ON {TABLE} USING spgist (geom)",
}


def drop_spatial_indexes() -> None:
    names = dbutil.scalar(f"""
        SELECT string_agg(format('%I.%I', schemaname, indexname), ',') FROM pg_indexes
        WHERE schemaname = 'dw' AND tablename = 'fact_position' AND indexdef ~* 'USING (gist|spgist)'""")
    for name in filter(None, names.split(",")):
        dbutil.run(["-c", f"DROP INDEX {name}"])


def explain(sql: str) -> dict:
    out = dbutil.run(["-A", "-t", "-c", f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {sql}"])
    return json.loads(out)[0]


def environment() -> str:
    lines = [f"measured_at_utc: {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())}",
             f"host_os: {platform.platform()}", f"host_cpu: {platform.processor() or platform.machine()}"]
    try:
        info = subprocess.run(["docker", "info", "--format",
                               "docker_cpus: {{.NCPU}}\ndocker_mem_bytes: {{.MemTotal}}\ndocker_kernel: {{.KernelVersion}}"],
                              capture_output=True, text=True).stdout.strip()
        lines.append(info)
    except OSError:
        lines.append("docker info: not available")
    lines.append("server: " + dbutil.scalar("SELECT version()"))
    lines.append("postgis: " + dbutil.scalar("SELECT postgis_lib_version()"))
    for setting in ("shared_buffers", "work_mem", "effective_cache_size", "max_parallel_workers_per_gather", "jit"):
        lines.append(f"{setting}: " + dbutil.scalar(f"SHOW {setting}"))
    lines.append(f"rows_in_{TABLE}: " + dbutil.scalar(f"SELECT count(*) FROM {TABLE}"))
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Spatial index benchmark (RQ3)")
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--warmups", type=int, default=2)
    args = parser.parse_args()

    (OUT / "plans").mkdir(parents=True, exist_ok=True)
    (OUT / "environment.txt").write_text(environment(), encoding="utf-8", newline="\n")

    timings, index_rows = [], []
    for config, ddl in CONFIGS.items():
        print(f"== index: {config}")
        drop_spatial_indexes()
        if ddl:
            start = time.perf_counter()
            dbutil.run(["-c", ddl])
            build_s = time.perf_counter() - start
            size = dbutil.scalar("SELECT pg_size_pretty(pg_relation_size('dw.bench_geom_idx'))")
            size_bytes = dbutil.scalar("SELECT pg_relation_size('dw.bench_geom_idx')")
            index_rows.append({"config": config, "build_seconds": round(build_s, 1),
                               "size": size, "size_bytes": size_bytes})
            print(f"   built in {build_s:.1f} s, size {size}")
        dbutil.run(["-c", f"VACUUM ANALYZE {TABLE}"])

        for qname, sql in QUERIES.items():
            for _ in range(args.warmups):
                explain(sql)
            for run_no in range(1, args.runs + 1):
                plan = explain(sql)
                top = plan["Plan"]
                timings.append({
                    "config": config, "query": qname, "run": run_no,
                    "execution_ms": round(plan["Execution Time"], 3),
                    "planning_ms": round(plan["Planning Time"], 3),
                    "shared_hit_blocks": top.get("Shared Hit Blocks", 0),
                    "shared_read_blocks": top.get("Shared Read Blocks", 0),
                })
            (OUT / "plans" / f"{config}_{qname}.json").write_text(
                json.dumps(plan, indent=2), encoding="utf-8", newline="\n")
            ms = [t["execution_ms"] for t in timings if t["config"] == config and t["query"] == qname]
            print(f"   {qname}: median {statistics.median(ms):,.2f} ms")

    drop_spatial_indexes()
    # Leave the warehouse with a GiST index, the usual choice, so later queries are fast.
    dbutil.run(["-c", CONFIGS["gist"].replace("bench_geom_idx", "fact_position_geom_gist")])

    with (OUT / "timings.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(timings[0]), lineterminator="\n")
        w.writeheader(); w.writerows(timings)
    with (OUT / "indexes.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(index_rows[0]), lineterminator="\n")
        w.writeheader(); w.writerows(index_rows)

    summary = []
    for config in CONFIGS:
        for qname in QUERIES:
            ms = sorted(t["execution_ms"] for t in timings if t["config"] == config and t["query"] == qname)
            q1, med, q3 = statistics.quantiles(ms, n=4, method="inclusive")
            summary.append({"config": config, "query": qname, "runs": len(ms),
                            "median_ms": round(med, 3), "q1_ms": round(q1, 3), "q3_ms": round(q3, 3),
                            "iqr_ms": round(q3 - q1, 3), "min_ms": ms[0], "max_ms": ms[-1]})
    base = {s["query"]: s["median_ms"] for s in summary if s["config"] == "none"}
    for s in summary:
        s["speedup_vs_none"] = round(base[s["query"]] / s["median_ms"], 1) if s["median_ms"] else ""
    with (OUT / "summary.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0]), lineterminator="\n")
        w.writeheader(); w.writerows(summary)
    print("Wrote results/bench/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
