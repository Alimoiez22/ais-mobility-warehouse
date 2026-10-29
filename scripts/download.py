"""Download one day of Danish Maritime Authority AIS data, reproducibly.

Usage (from the repository root):
    uv run python scripts/download.py --date 2026-10-26

What it does:
1. Downloads aisdk-<date>.zip into data/ (skipped if already present).
2. Computes the file's SHA-256 checksum.
3. First run: records URL, size, checksum and server timestamp in
   data.lock.json, which IS committed to Git. Later runs: refuses to
   continue if the checksum differs, so every result is traceable to
   exactly one input file.
4. Tests the zip and extracts the CSV into data/.

Only the Python standard library is used, so there is nothing to install.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_BASE_URL = "http://aisdata.ais.dk/"  # linked from dma.dk "Get historical AIS data"
REPO_ROOT = Path(__file__).resolve().parent.parent
LOCK_FILE = REPO_ROOT / "data.lock.json"
CHUNK = 1024 * 1024  # read and hash 1 MB at a time, so memory use stays small


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while block := f.read(CHUNK):
            digest.update(block)
    return digest.hexdigest()


def download(url: str, target: Path) -> str | None:
    """Stream url to target via a .part file; return the server's Last-Modified header."""
    partial = target.with_suffix(target.suffix + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": "ais-mobility-warehouse/0.1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        total = int(response.headers.get("Content-Length", 0))
        last_modified = response.headers.get("Last-Modified")
        done, next_report = 0, 0.0
        with partial.open("wb") as out:
            while block := response.read(CHUNK):
                out.write(block)
                done += len(block)
                if total and done / total >= next_report:
                    print(f"  {done / total:6.1%}  {done / 1e6:8.1f} / {total / 1e6:.1f} MB")
                    next_report += 0.10
    if total and done != total:
        raise RuntimeError(f"Incomplete download: got {done} of {total} bytes")
    partial.replace(target)  # rename only once the file is complete
    return last_modified


def safe_extract_csv(zip_path: Path, data_dir: Path) -> Path:
    """Extract the single CSV. Member names are checked so a malicious archive
    cannot write outside data/ (the 'zip slip' attack)."""
    with zipfile.ZipFile(zip_path) as archive:
        bad = archive.testzip()
        if bad is not None:
            raise RuntimeError(f"Corrupt member in zip: {bad}")
        csv_members = [m for m in archive.infolist() if m.filename.lower().endswith(".csv")]
        if len(csv_members) != 1:
            raise RuntimeError(f"Expected exactly one CSV, found {[m.filename for m in csv_members]}")
        member = csv_members[0]
        name = Path(member.filename).name
        if name != member.filename or name.startswith("."):
            raise RuntimeError(f"Unsafe file name in zip: {member.filename!r}")
        target = data_dir / name
        if target.exists() and target.stat().st_size == member.file_size:
            print(f"CSV already extracted: {target.name}")
            return target
        print(f"Extracting {name} ({member.file_size / 1e9:.2f} GB uncompressed)...")
        with archive.open(member) as src, target.open("wb") as dst:
            shutil.copyfileobj(src, dst, CHUNK)
        return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--date", required=True, help="day to fetch, YYYY-MM-DD")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data")
    parser.add_argument("--min-free-gb", type=float, default=10.0,
                        help="refuse to start below this much free disk (default 10)")
    args = parser.parse_args()

    try:
        datetime.strptime(args.date, "%Y-%m-%d")  # fail early on a badly typed date
    except ValueError:
        parser.error(f"--date must be a real date in YYYY-MM-DD form, got {args.date!r}")
    filename = f"aisdk-{args.date}.zip"
    url = args.base_url.rstrip("/") + "/" + filename
    args.data_dir.mkdir(parents=True, exist_ok=True)
    zip_path = args.data_dir / filename

    lock = json.loads(LOCK_FILE.read_text()) if LOCK_FILE.exists() else {}
    pinned = lock.get(filename)

    free_gb = shutil.disk_usage(args.data_dir).free / 1e9
    print(f"Free disk where data/ lives: {free_gb:.1f} GB")
    if free_gb < args.min_free_gb:
        print(f"Stopping: less than {args.min_free_gb:g} GB free.", file=sys.stderr)
        return 1

    last_modified = pinned.get("last_modified") if pinned else None
    if zip_path.exists():
        print(f"Zip already present: {zip_path.name}")
    else:
        print(f"Downloading {url}")
        try:
            last_modified = download(url, zip_path)
        except (urllib.error.URLError, TimeoutError, RuntimeError) as err:
            print(
                f"Download failed: {err}\n"
                "Check that the file is listed at the source, or pass --base-url if its address changed.",
                file=sys.stderr,
            )
            return 3

    print("Computing SHA-256...")
    checksum = sha256_of(zip_path)
    size = zip_path.stat().st_size

    if pinned is None:
        lock[filename] = {
            "url": url,
            "bytes": size,
            "sha256": checksum,
            "last_modified": last_modified,
            "pinned_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        LOCK_FILE.write_text(json.dumps(lock, indent=2) + "\n")
        print(f"Pinned new file in {LOCK_FILE.name}: sha256 {checksum}")
    elif pinned["sha256"] != checksum:
        print(
            f"CHECKSUM MISMATCH for {filename}\n  expected {pinned['sha256']}\n  got      {checksum}\n"
            "The source file changed or the download is damaged. Delete the zip and retry;\n"
            "if it still differs, the provider republished the file. Do not continue silently.",
            file=sys.stderr,
        )
        return 2
    else:
        print("Checksum matches data.lock.json")

    csv_path = safe_extract_csv(zip_path, args.data_dir)
    print(f"Done: {zip_path.name} {size / 1e6:.1f} MB, {csv_path.name} {csv_path.stat().st_size / 1e9:.2f} GB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
