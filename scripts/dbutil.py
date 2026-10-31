"""Shared helper: run SQL against the project database through `docker compose exec psql`.

Only small results go through this path (query outputs, plans, timings). The bulk CSV
load is the one step that moves large data, and it has its own path (make load).
Set AIS_PSQL to override the command, e.g. for testing against another server.
"""

from __future__ import annotations

import csv
import io
import os
import shlex
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


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


def psql_base() -> list[str]:
    env = read_env()
    if env.get("AIS_PSQL"):
        base = shlex.split(env["AIS_PSQL"])
    else:
        base = ["docker", "compose", "exec", "-T", "db", "psql",
                "-U", env.get("POSTGRES_USER", "ais"), "-d", env.get("POSTGRES_DB", "ais")]
    return [*base, "-X", "-q", "-v", "ON_ERROR_STOP=1"]


def run(args: list[str]) -> str:
    proc = subprocess.run([*psql_base(), *args], capture_output=True, text=True, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"psql failed ({' '.join(args)[:120]}):\n{proc.stderr.strip()}")
    return proc.stdout


def query_csv(sql: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(run(["--csv", "-c", sql]))))


def scalar(sql: str) -> str:
    return run(["-A", "-t", "-c", sql]).strip()
