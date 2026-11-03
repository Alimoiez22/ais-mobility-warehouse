"""Build the results dashboard, docs/index.html, from files the pipeline already wrote.

Usage: uv run python scripts/dashboard.py   (normally through `make dashboard`)

Inputs
  results/*.csv            cleaning log, hourly traffic, warehouse counts, OLAP runtimes, benchmark
  data/trip_tracks.csv     one simplified line per trip (sql/45_trip_tracks.sql)
  data/ne_land_10m.json    Natural Earth 1:10m land (public domain), downloaded once on first run

Output
  docs/index.html          one self-contained page: no map tiles, no web services, no libraries.
                           It works opened from disk, on GitHub Pages, or as a shared link.

Design choices
  * The coastline is drawn from Natural Earth data embedded in the page, clipped to the study
    area. Tile servers (OpenStreetMap, CARTO) refuse pages opened from a file, and a page that
    depends on a third-party service breaks when that service changes its rules.
  * Coordinates are stored as integer deltas (1e-4 degrees for tracks, 1e-3 for land), which
    keeps 4,000+ routes small enough to embed.
  * Ship types are grouped into three colour groups plus "Other": with more than three hues on
    one map, some pairs cannot be told apart by colour-blind readers.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
R = ROOT / "results"
DATA = ROOT / "data"
OUT = ROOT / "docs" / "index.html"
REPO_URL = "https://github.com/Alimoiez22/ais-mobility-warehouse"

LAND_FILE = DATA / "ne_land_10m.json"
# world-atlas 2.0.2 on jsDelivr: Natural Earth 1:10m land as TopoJSON. A pinned package
# version, so the bytes never change; the SHA-256 is printed on download for the record.
LAND_URL = "https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/land-10m.json"
# Area drawn on the map (a little larger than the cleaning rule's 53-59 N, 2-17 E box).
BBOX = (2.0, 53.0, 17.0, 59.0)  # lon_min, lat_min, lon_max, lat_max
CLIP = (1.0, 52.5, 18.0, 59.5)

GROUPS = [  # (key, label, ship types)  - order = colour slot order
    ("cargo", "Cargo & tanker", {"Cargo", "Tanker"}),
    ("passenger", "Passenger & ferry", {"Passenger", "HSC"}),
    ("fishing", "Fishing", {"Fishing"}),
    ("other", "Other", None),  # everything else: leisure, service, unknown
]


# --------------------------------------------------------------------------- inputs

def read(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        print(f"  (missing {path.relative_to(ROOT)}, section left out)")
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def fnum(v, default=0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def ensure_land() -> dict | None:
    if not LAND_FILE.exists():
        print(f"  downloading coastline: {LAND_URL}")
        try:
            req = urllib.request.Request(LAND_URL, headers={"User-Agent": "ais-mobility-warehouse"})
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
            LAND_FILE.write_bytes(raw)
            print(f"  saved {LAND_FILE.relative_to(ROOT)} ({len(raw):,} bytes, sha256 {hashlib.sha256(raw).hexdigest()})")
        except Exception as e:  # noqa: BLE001 - the map still works without a coastline
            print(f"  could not download the coastline ({e}).")
            print(f"  Download it yourself to {LAND_FILE.relative_to(ROOT)} and rerun, e.g.:")
            print(f"    curl.exe -L -o data/ne_land_10m.json {LAND_URL}")
            return None
    return json.loads(LAND_FILE.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- geometry

def topo_polygons(topo: dict) -> list[list[list[tuple[float, float]]]]:
    """Decode the 'land' object of a TopoJSON file into polygons (lists of rings of lon/lat)."""
    sx, sy = topo["transform"]["scale"]
    tx, ty = topo["transform"]["translate"]
    arcs = []
    for arc in topo["arcs"]:
        x = y = 0
        pts = []
        for dx, dy, *_ in arc:
            x += dx
            y += dy
            pts.append((x * sx + tx, y * sy + ty))
        arcs.append(pts)

    def ring(indexes):
        out: list[tuple[float, float]] = []
        for i in indexes:
            pts = arcs[i] if i >= 0 else arcs[~i][::-1]
            out.extend(pts if not out else pts[1:])
        return out

    def geoms(g):
        if g["type"] == "GeometryCollection":
            for sub in g["geometries"]:
                yield from geoms(sub)
        elif g["type"] == "Polygon":
            yield [ring(r) for r in g["arcs"]]
        elif g["type"] == "MultiPolygon":
            for p in g["arcs"]:
                yield [ring(r) for r in p]

    obj = topo["objects"].get("land") or next(iter(topo["objects"].values()))
    return list(geoms(obj))


def clip_ring(pts, box):
    """Sutherland-Hodgman: clip a closed ring to an axis-aligned rectangle."""
    x0, y0, x1, y1 = box
    edges = [
        (lambda p: p[0] >= x0, lambda a, b: (x0, a[1] + (b[1] - a[1]) * (x0 - a[0]) / (b[0] - a[0]))),
        (lambda p: p[0] <= x1, lambda a, b: (x1, a[1] + (b[1] - a[1]) * (x1 - a[0]) / (b[0] - a[0]))),
        (lambda p: p[1] >= y0, lambda a, b: (a[0] + (b[0] - a[0]) * (y0 - a[1]) / (b[1] - a[1]), y0)),
        (lambda p: p[1] <= y1, lambda a, b: (a[0] + (b[0] - a[0]) * (y1 - a[1]) / (b[1] - a[1]), y1)),
    ]
    out = pts
    for inside, cross in edges:
        if not out:
            break
        src, out = out, []
        prev = src[-1]
        for cur in src:
            if inside(cur):
                if not inside(prev):
                    out.append(cross(prev, cur))
                out.append(cur)
            elif inside(prev):
                out.append(cross(prev, cur))
            prev = cur
    return out


def encode(pts, scale: int) -> list[int]:
    """Flatten [(lon, lat), ...] to integer deltas [x0, y0, dx1, dy1, ...], dropping repeats."""
    out: list[int] = []
    px = py = None
    for lon, lat in pts:
        x, y = round(lon * scale), round(lat * scale)
        if (x, y) == (px, py):
            continue
        if px is None:
            out += [x, y]
        else:
            out += [x - px, y - py]
        px, py = x, y
    return out


def land_rings(topo: dict | None) -> list[list[int]]:
    if topo is None:
        return []
    rings = []
    for poly in topo_polygons(topo):
        for r in poly:
            if len(r) < 3:
                continue
            xs = [p[0] for p in r]
            ys = [p[1] for p in r]
            if max(xs) < CLIP[0] or min(xs) > CLIP[2] or max(ys) < CLIP[1] or min(ys) > CLIP[3]:
                continue
            c = clip_ring(r, CLIP)
            e = encode(c, 1000)
            if len(e) >= 6:
                rings.append(e)
    return rings


def group_of(ship_type: str) -> int:
    for i, (_, _, types) in enumerate(GROUPS):
        if types is None or ship_type in types:
            return i
    return len(GROUPS) - 1


def tracks() -> list[list]:
    rows = read(DATA / "trip_tracks.csv")
    out = []
    for r in rows:
        try:
            g = json.loads(r["geojson"])
        except (KeyError, json.JSONDecodeError):
            continue
        lines = [g["coordinates"]] if g["type"] == "LineString" else g.get("coordinates", [])
        for line in lines:
            e = encode(line, 10000)
            if len(e) < 4:
                continue
            out.append([group_of(r["ship_type"]), r["name"].strip().title() or "Unnamed", r["ship_type"],
                        fnum(r["length_km"]), int(fnum(r["duration_min"])), fnum(r["avg_speed_kn"], None),
                        r["start_utc"], r["end_utc"], e])
    return out


# --------------------------------------------------------------------------- page data

def plan_facts(config: str, query: str) -> dict:
    """Pages read and the scan type, from the saved EXPLAIN (ANALYZE, BUFFERS) plan."""
    path = R / "bench" / "plans" / f"{config}_{query}.json"
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
        top = (plan[0] if isinstance(plan, list) else plan)["Plan"]
    except (OSError, ValueError, KeyError, IndexError):
        return {}
    scans = []

    def walk(n):
        if "Scan" in n.get("Node Type", "") and "Bitmap Index" not in n.get("Node Type", ""):
            scans.append(n["Node Type"])
        for c in n.get("Plans", []):
            walk(c)
    walk(top)
    return {"pages": int(top.get("Shared Hit Blocks", 0) + top.get("Shared Read Blocks", 0)),
            "scan": scans[0] if scans else ""}


def build_data() -> dict:
    clean = read(R / "cleaning.csv")
    hourly = read(R / "hourly_traffic.csv")
    star = {s["table_name"]: int(fnum(s["row_count"])) for s in read(R / "star_counts.csv")}
    olap = read(R / "olap_runtimes.csv")
    bench = read(R / "bench" / "summary.csv")
    q1 = read(R / "olap" / "q1_traffic_by_type_and_daypart.csv")

    raw = int(fnum(clean[0]["rows_before"])) if clean else 0
    kept = int(fnum(clean[-1]["rows_after"])) if clean else 0

    fleet = sorted(((r["ship_type"], int(fnum(r["ships"])), int(fnum(r["reports"])))
                    for r in q1 if r["day_part"] == "(whole day)" and r["ship_type"] != "(all types)"),
                   key=lambda t: -t[1])
    top, rest = fleet[:9], fleet[9:]
    if rest:
        top.append((f"{len(rest)} other types", sum(t[1] for t in rest), sum(t[2] for t in rest)))

    bench_rows = [{"config": b["config"], "query": b["query"], "median": fnum(b["median_ms"]),
                   "q1": fnum(b["q1_ms"]), "q3": fnum(b["q3_ms"]), "speedup": fnum(b["speedup_vs_none"]),
                   **plan_facts(b["config"], b["query"])}
                  for b in bench]
    best = max(bench_rows, key=lambda b: b["speedup"] if b["query"] != "B3_knn_10" else 0, default=None)

    trk = tracks()
    land = land_rings(ensure_land())
    print(f"  map: {len(trk):,} trip lines, {len(land):,} coastline rings")

    return {
        "kpi": {"raw": raw, "kept": kept, "ships": star.get("dim_ship", 0), "trips": star.get("fact_trip", 0),
                "best": best},
        "clean": [{"step": int(fnum(c["step"])), "rule": c["rule"], "removed": int(fnum(c["rows_removed"])),
                   "pct": fnum(c["pct_of_raw"]), "desc": c["description"]} for c in clean if fnum(c["step"]) > 0],
        "hourly": [{"h": int(fnum(h["hour"])), "ships": int(fnum(h["ships"])), "reports": int(fnum(h["reports"]))}
                   for h in hourly],
        "fleet": [{"type": t, "ships": s, "reports": rp} for t, s, rp in top],
        "olap": [{"q": o["query"], "question": o["question"].split(": ", 1)[-1], "rows": int(fnum(o["result_rows"])),
                  "ms": fnum(o["execution_ms"])} for o in olap],
        "bench": bench_rows,
        "groups": [label for _, label, _ in GROUPS],
        "bbox": BBOX,
        "tracks": trk,
        "land": land,
        "built": datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC"),
        "repo": REPO_URL,
    }


def main() -> int:
    data = build_data()
    template = (Path(__file__).with_name("dashboard_template.html")).read_text(encoding="utf-8")
    payload = json.dumps(data, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
    head, body = template.split("<!-- body -->", 1)
    page = ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n" + head.strip() +
            "\n</head>\n<body>\n" + body.strip().replace("__DATA__", payload) + "\n</body>\n</html>\n")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page, encoding="utf-8", newline="\n")
    print(f"Wrote {OUT.relative_to(ROOT)} ({len(page.encode('utf-8')) / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
