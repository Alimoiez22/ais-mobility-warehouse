"""Run the 8 OLAP queries (sql/olap/q*.sql), save each result and its runtime.

Usage: uv run python scripts/run_olap.py

Writes results/olap/<query>.csv and results/olap_runtimes.csv.
The runtime is the server-side execution time from EXPLAIN (ANALYZE), measured on a
second run so the data is in cache (the first run is a warm-up). This avoids counting
the Docker and psql start-up overhead.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dbutil  # noqa: E402

SQL_DIR = dbutil.REPO_ROOT / "sql" / "olap"
OUT_DIR = dbutil.REPO_ROOT / "results" / "olap"


def question_of(sql: str) -> str:
    for line in sql.splitlines():
        if line.startswith("-- Q"):
            return line[3:].strip()
    return ""


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for path in sorted(SQL_DIR.glob("q*.sql")):
        sql = path.read_text(encoding="utf-8")
        body = "\n".join(l for l in sql.splitlines() if not l.strip().startswith("--")).strip().rstrip(";")
        print(f"{path.stem}...")
        result = dbutil.run(["--csv", "-f", f"/sql/olap/{path.name}"])
        (OUT_DIR / f"{path.stem}.csv").write_text(result, encoding="utf-8", newline="\n")
        n_rows = max(len(result.strip().splitlines()) - 1, 0)
        plan = json.loads(dbutil.run(["-A", "-t", "-c", f"EXPLAIN (ANALYZE, FORMAT JSON) {body}"]))
        exec_ms = plan[0]["Execution Time"]
        rows.append({"query": path.stem, "question": question_of(sql),
                     "result_rows": n_rows, "execution_ms": round(exec_ms, 1)})
        print(f"  {n_rows} rows, {exec_ms:,.0f} ms")
    with (dbutil.REPO_ROOT / "results" / "olap_runtimes.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print("Wrote results/olap/*.csv and results/olap_runtimes.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
