"""Profile the raw AIS staging table and write results/profile.md.

Usage (from the repository root, database running via `make up`):
    uv run python scripts/profile.py

It answers "what is wrong with the raw data?" with counts, not opinions:
  1. Overview: rows, ships, object types
  2. Completeness: per column, how many values are NULL, empty or a placeholder
  3. Numeric fields: values that are not numbers, min/max, out-of-range counts,
     and AIS "not available" codes
  4. Timestamps: unparseable values and values outside the file's day
  5. MMSI identifiers: length and prefix patterns
  6. Duplicates: exact duplicate rows and same-ship-same-second reports
  7. Top values of the main categorical columns

It does not decide anything. The cleaning rules are chosen by a person after
reading the report.

Only the Python standard library is used. SQL is sent to the database with
`docker compose exec ... psql --csv`, which is fine for small result sets
(the bulk load is the only step that moves large data).
"""

from __future__ import annotations

import argparse
import csv
import io
import os
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TABLE = "staging.ais_raw"

ALL_COLUMNS = [
    "ts", "type_of_mobile", "mmsi", "latitude", "longitude", "nav_status", "rot",
    "sog", "cog", "heading", "imo", "callsign", "name", "ship_type", "cargo_type",
    "width", "length", "pos_fixing_device", "draught", "destination", "eta",
    "data_source_type", "dim_a", "dim_b", "dim_c", "dim_d",
]
PLACEHOLDERS = ("Unknown", "Undefined", "Unknown value")
NUMBER_RE = r"^-?[0-9]+(\.[0-9]+)?$"

# Numeric fields: (column, valid_min, valid_max, AIS "not available" code or None, unit)
# The not-available codes come from the AIS message standard (ITU-R M.1371).
NUMERIC_FIELDS = [
    ("latitude", -90, 90, 91, "degrees"),
    ("longitude", -180, 180, 181, "degrees"),
    ("sog", 0, 102.2, 102.3, "knots"),
    ("cog", 0, 359.9, 360, "degrees"),
    ("heading", 0, 359, 511, "degrees"),
    ("rot", -720, 720, None, "degrees/min"),
    ("draught", 0, 25.5, None, "metres"),
    # Ship size is reported as antenna-to-side distances: A, B up to 511 m and
    # C, D up to 63 m each, so width = C + D <= 126 and length = A + B <= 1022.
    ("width", 0, 126, None, "metres"),
    ("length", 0, 1022, None, "metres"),
]
CATEGORICAL = ["type_of_mobile", "nav_status", "ship_type", "pos_fixing_device", "data_source_type"]


class Database:
    def __init__(self, psql_cmd: list[str]):
        self.psql_cmd = psql_cmd
        self.timings: list[tuple[str, float]] = []

    def query(self, label: str, sql: str) -> list[dict[str, str]]:
        start = time.perf_counter()
        proc = subprocess.run(
            [*self.psql_cmd, "-c", sql],
            capture_output=True, text=True, encoding="utf-8",
        )
        if proc.returncode != 0:
            raise RuntimeError(f"Query '{label}' failed:\n{proc.stderr.strip()}")
        self.timings.append((label, time.perf_counter() - start))
        return list(csv.DictReader(io.StringIO(proc.stdout)))


def read_env() -> dict[str, str]:
    values: dict[str, str] = {}
    path = REPO_ROOT / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
    return {**values, **os.environ}


def fmt(n: str | int | float | None) -> str:
    if n is None or n == "":
        return ""
    try:
        f = float(n)
    except ValueError:
        return str(n)
    return f"{int(f):,}" if f.is_integer() else f"{f:,.3f}"


def pct(part: str | int, whole: int) -> str:
    return f"{100 * int(part) / whole:.2f}%" if whole else ""


def md_table(headers: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    out += ["| " + " | ".join(str(c).replace("|", "\\|") for c in r) + " |" for r in rows]
    return "\n".join(out)


def num(col: str) -> str:
    """SQL expression: the column as numeric if it looks like a number, else NULL."""
    return f"CASE WHEN {col} ~ '{NUMBER_RE}' THEN {col}::numeric END"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--psql-cmd", help="override the psql command (used for testing)")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "results" / "profile.md")
    args = parser.parse_args()

    if args.psql_cmd:
        base = shlex.split(args.psql_cmd)
    else:
        env = read_env()
        base = ["docker", "compose", "exec", "-T", "db", "psql",
                "-U", env.get("POSTGRES_USER", "ais"), "-d", env.get("POSTGRES_DB", "ais")]
    db = Database([*base, "-X", "-v", "ON_ERROR_STOP=1", "--csv"])
    started = time.perf_counter()
    md: list[str] = []

    # 1. Overview ---------------------------------------------------------------
    print("1/7 overview...")
    ov = db.query("overview", f"""
        SELECT count(*) AS rows, count(DISTINCT mmsi) AS mmsi_distinct,
               count(DISTINCT type_of_mobile) AS mobile_types
        FROM {TABLE}""")[0]
    total = int(ov["rows"])
    types = db.query("type_of_mobile", f"""
        SELECT coalesce(type_of_mobile, '(NULL)') AS value, count(*) AS rows,
               count(DISTINCT mmsi) AS mmsi
        FROM {TABLE} GROUP BY 1 ORDER BY 2 DESC""")
    md += [
        "# Raw AIS data profile",
        "",
        f"Table `{TABLE}`, generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC by `scripts/profile.py`.",
        "All counts are measured on the full table. Nothing has been removed yet.",
        "",
        "## 1. Overview",
        "",
        md_table(["Measure", "Value"], [
            ["Rows", fmt(total)],
            ["Distinct MMSI (transmitter IDs)", fmt(ov["mmsi_distinct"])],
            ["Distinct 'Type of mobile' values", fmt(ov["mobile_types"])],
        ]),
        "",
        "Rows by type of mobile (what kind of transmitter sent the report):",
        "",
        md_table(["Type of mobile", "Rows", "% of rows", "Distinct MMSI"],
                 [[t["value"], fmt(t["rows"]), pct(t["rows"], total), fmt(t["mmsi"])] for t in types]),
        "",
    ]

    # 2. Completeness ---------------------------------------------------------------
    print("2/7 completeness (one scan over all columns)...")
    ph = ", ".join(f"'{p}'" for p in PLACEHOLDERS)
    exprs = []
    for c in ALL_COLUMNS:
        exprs += [f"count(*) FILTER (WHERE {c} IS NULL) AS {c}__null",
                  f"count(*) FILTER (WHERE {c} = '') AS {c}__empty",
                  f"count(*) FILTER (WHERE {c} IN ({ph})) AS {c}__placeholder"]
    comp = db.query("completeness", f"SELECT {', '.join(exprs)} FROM {TABLE}")[0]
    rows = []
    for c in ALL_COLUMNS:
        n, e, p = int(comp[f"{c}__null"]), int(comp[f"{c}__empty"]), int(comp[f"{c}__placeholder"])
        rows.append([f"`{c}`", fmt(n), fmt(e), fmt(p), pct(n + e + p, total)])
    md += [
        "## 2. Completeness",
        "",
        "Missing information appears in two forms: an empty field (loaded as NULL) or a",
        f"placeholder word ({', '.join(repr(p) for p in PLACEHOLDERS)}).",
        "",
        md_table(["Column", "NULL", "Empty string", "Placeholder", "Missing in any form"], rows),
        "",
    ]

    # 3. Numeric fields -----------------------------------------------------------
    print("3/7 numeric fields...")
    exprs = []
    for col, lo, hi, na, _ in NUMERIC_FIELDS:
        v = num(col)
        exprs += [
            f"count(*) FILTER (WHERE {col} IS NOT NULL AND NOT {col} ~ '{NUMBER_RE}') AS {col}__not_number",
            f"min({v}) AS {col}__min", f"max({v}) AS {col}__max",
            f"count(*) FILTER (WHERE {v} < {lo} OR {v} > {hi}) AS {col}__out_of_range",
        ]
        exprs.append(f"count(*) FILTER (WHERE {v} = {na}) AS {col}__na_code" if na is not None
                     else f"NULL AS {col}__na_code")
    nf = db.query("numeric", f"SELECT {', '.join(exprs)} FROM {TABLE}")[0]
    rows = []
    for col, lo, hi, na, unit in NUMERIC_FIELDS:
        rows.append([
            f"`{col}`", unit, f"{lo} to {hi}", fmt(nf[f"{col}__not_number"]),
            fmt(nf[f"{col}__min"]), fmt(nf[f"{col}__max"]), fmt(nf[f"{col}__out_of_range"]),
            "" if na is None else f"{na}: {fmt(nf[f'{col}__na_code'])}",
        ])
    md += [
        "## 3. Numeric fields",
        "",
        "Values are text in staging. 'Not a number' counts values that are present but cannot be",
        "read as a number. 'Out of range' counts numbers outside the valid range shown, and it",
        "includes the AIS 'not available' code where that code lies outside the range",
        "(for example heading 511). The valid ranges and codes follow the AIS message standard",
        "(ITU-R M.1371); `rot` is the value as delivered in the file.",
        "",
        md_table(["Column", "Unit", "Valid range", "Not a number", "Min", "Max",
                  "Out of range", "'Not available' code: rows"], rows),
        "",
    ]

    # 4. Timestamps -------------------------------------------------------------
    print("4/7 timestamps...")
    ts_re = r"^[0-9]{2}/[0-9]{2}/[0-9]{4} [0-9]{2}:[0-9]{2}:[0-9]{2}$"
    tsq = db.query("timestamps", f"""
        WITH t AS (
            SELECT ts, CASE WHEN ts ~ '{ts_re}' THEN to_timestamp(ts, 'DD/MM/YYYY HH24:MI:SS')::timestamp END AS t
            FROM {TABLE})
        SELECT count(*) FILTER (WHERE ts IS NULL) AS null_ts,
               count(*) FILTER (WHERE ts IS NOT NULL AND t IS NULL) AS unparseable,
               min(t)::text AS first_ts, max(t)::text AS last_ts,
               count(*) FILTER (WHERE t IS NOT NULL AND t::date <> DATE '2026-10-26') AS outside_day
        FROM t""")[0]
    hours = db.query("rows_per_hour", f"""
        SELECT substr(ts, 12, 2) AS hour, count(*) AS rows FROM {TABLE}
        WHERE ts ~ '{ts_re}' GROUP BY 1 ORDER BY 1""")
    md += [
        "## 4. Timestamps",
        "",
        "Format in the file: `dd/mm/yyyy hh:mm:ss`. The time zone is not stated in the row itself.",
        "",
        md_table(["Measure", "Value"], [
            ["NULL", fmt(tsq["null_ts"])],
            ["Present but not in the expected format", fmt(tsq["unparseable"])],
            ["Earliest", tsq["first_ts"]], ["Latest", tsq["last_ts"]],
            ["Outside 26 Oct 2026", fmt(tsq["outside_day"])],
        ]),
        "",
        "Rows per hour of the day:",
        "",
        md_table(["Hour", "Rows", "% of rows"], [[h["hour"], fmt(h["rows"]), pct(h["rows"], total)] for h in hours]),
        "",
    ]

    # 5. MMSI -----------------------------------------------------------------------
    print("5/7 MMSI patterns...")
    mm = db.query("mmsi", f"""
        SELECT CASE
                 WHEN mmsi IS NULL THEN '(NULL)'
                 WHEN mmsi !~ '^[0-9]+$' THEN 'not all digits'
                 WHEN length(mmsi) <> 9 THEN 'digits, length ' || length(mmsi)
                 WHEN mmsi LIKE '00%' THEN '9 digits, starts 00'
                 WHEN mmsi LIKE '0%' THEN '9 digits, starts 0'
                 WHEN mmsi LIKE '111%' THEN '9 digits, starts 111'
                 WHEN mmsi LIKE '97%' THEN '9 digits, starts 97'
                 WHEN mmsi LIKE '98%' THEN '9 digits, starts 98'
                 WHEN mmsi LIKE '99%' THEN '9 digits, starts 99'
                 WHEN left(mmsi, 1) BETWEEN '2' AND '7' THEN '9 digits, starts 2-7'
                 ELSE '9 digits, other start'
               END AS pattern,
               count(*) AS rows, count(DISTINCT mmsi) AS mmsi
        FROM {TABLE} GROUP BY 1 ORDER BY 2 DESC""")
    md += [
        "## 5. MMSI identifiers",
        "",
        "An MMSI is a 9-digit radio identity. By the ITU numbering scheme, ships normally start",
        "with a country code 2-7; other prefixes are used for coast stations (00), SAR aircraft",
        "(111), safety devices (97), craft associated with a parent ship (98) and aids to",
        "navigation (99). This table only counts patterns; it does not judge them.",
        "",
        md_table(["Pattern", "Rows", "% of rows", "Distinct MMSI"],
                 [[m["pattern"], fmt(m["rows"]), pct(m["rows"], total), fmt(m["mmsi"])] for m in mm]),
        "",
    ]

    # 6. Duplicates ---------------------------------------------------------------
    print("6/7 duplicates (the slowest step, a few minutes)...")
    all_cols = ", ".join(ALL_COLUMNS)
    dup = db.query("duplicates", f"""
        SELECT count(*) - count(DISTINCT md5(ROW({all_cols})::text)) AS exact_dupe_extra_rows,
               count(*) - count(DISTINCT (mmsi, ts)) AS same_mmsi_ts_extra_rows
        FROM {TABLE}""")[0]
    md += [
        "## 6. Duplicates",
        "",
        md_table(["Kind", "Extra rows (beyond the first copy)", "% of rows"], [
            ["Exact duplicates (all 26 columns identical)", fmt(dup["exact_dupe_extra_rows"]),
             pct(dup["exact_dupe_extra_rows"], total)],
            ["Same MMSI and same timestamp (other columns may differ)", fmt(dup["same_mmsi_ts_extra_rows"]),
             pct(dup["same_mmsi_ts_extra_rows"], total)],
        ]),
        "",
        "Exact duplicates are a subset of same-MMSI-same-timestamp rows.",
        "",
    ]

    # 7. Categorical columns --------------------------------------------------------
    print("7/7 top values of categorical columns...")
    md += ["## 7. Top values of categorical columns", ""]
    for col in CATEGORICAL:
        top = db.query(f"top_{col}", f"""
            SELECT coalesce({col}, '(NULL)') AS value, count(*) AS rows
            FROM {TABLE} GROUP BY 1 ORDER BY 2 DESC LIMIT 15""")
        md += [f"### `{col}` (top 15)", "",
               md_table(["Value", "Rows", "% of rows"], [[t["value"], fmt(t["rows"]), pct(t["rows"], total)] for t in top]),
               ""]

    # Footer --------------------------------------------------------------------
    elapsed = time.perf_counter() - started
    md += [
        "## Query timings",
        "",
        md_table(["Query", "Seconds"], [[label, f"{s:.1f}"] for label, s in db.timings]),
        "",
        f"Total: {elapsed:.0f} s.",
        "",
    ]
    args.out.parent.mkdir(exist_ok=True)
    args.out.write_text("\n".join(md), encoding="utf-8", newline="\n")
    print(f"Wrote {args.out.relative_to(REPO_ROOT) if args.out.is_relative_to(REPO_ROOT) else args.out} in {elapsed:.0f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
