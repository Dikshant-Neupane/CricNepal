#!/usr/bin/env python3
"""In-season daily update for NPL Season 3 (Oct 26 - Nov 21, 2026).

One command that performs the whole match-day flow from
docs/S3_INGESTION_RUNBOOK.md:

  1. download the latest cricsheet NPL bundle
  2. ingest new matches (scripts/ingest_cricsheet.py --append, idempotent)
  3. rebuild derived data (src.preprocessing.normalize_data, refresh_all.py)
  4. print a compact summary of what changed

Safe to run any time: appends merge only new match_ids, a failed download
aborts before anything is touched, and a lockfile prevents overlapping
runs. Exits 0 when all steps succeed (including "no new matches"), 1 on
the first failed step (later steps are skipped).

Run logs land in logs/inseason/<date>.log (gitignored).
The bundle URL can be overridden with CRICSHEET_URL (used by tests).
"""

import os
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUNDLE_URL = os.environ.get(
    "CRICSHEET_URL", "https://cricsheet.org/downloads/npl_json.zip"
)
LOCK = ROOT / "logs" / "inseason" / ".lock"


def pick_python() -> str:
    """Full-deps audit venv first (normalize/refresh need it), then the
    project venv, then the interpreter running this script."""
    for cand in (
        Path.home() / "workspace" / ".scratch" / "cric-audit-venv" / "bin" / "python",
        ROOT / ".venv" / "bin" / "python",
    ):
        if cand.exists():
            return str(cand)
    return sys.executable


def parquet_counts() -> tuple[int, int, set]:
    import pandas as pd

    matches = pd.read_parquet(ROOT / "data" / "final" / "parquet" / "matches.parquet")
    deliveries = pd.read_parquet(
        ROOT / "data" / "final" / "parquet" / "ball_by_ball.parquet",
        columns=["match_id"],
    )
    return len(matches), len(deliveries), set(matches["match_id"].astype(str))


def new_match_lines(new_ids: set) -> list[str]:
    if not new_ids:
        return []
    import pandas as pd

    matches = pd.read_parquet(ROOT / "data" / "final" / "parquet" / "matches.parquet")
    rows = matches[matches["match_id"].astype(str).isin(new_ids)]
    lines = []
    for _, r in rows.sort_values("match_date").iterrows():
        lines.append(
            f"  + {r['match_date']}  {r['team_1_name']} vs {r['team_2_name']}"
            f"  ({r['match_id']})"
        )
    return lines


def run_step(name: str, argv: list[str], log) -> bool:
    log.write(f"\n===== {name}: {' '.join(argv)}\n")
    log.flush()
    proc = subprocess.run(argv, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    ok = proc.returncode == 0
    log.write(f"===== {name}: exit {proc.returncode}\n")
    log.flush()
    print(f"STEP {name}: {'OK' if ok else 'FAIL'}")
    return ok


def main() -> int:
    log_dir = ROOT / "logs" / "inseason"
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    log_path = log_dir / f"{stamp}.log"

    if LOCK.exists():
        print("STATUS FAIL: another inseason_update run holds the lock "
              f"({LOCK}); if no run is active, delete it and retry.")
        return 1
    LOCK.write_text(stamp)

    try:
        with open(log_path, "w") as log:
            py = pick_python()
            print(f"python: {py}")
            log.write(f"python: {py}\nurl: {BUNDLE_URL}\n")

            m0, d0, ids0 = parquet_counts()

            # 1. Download + verify the bundle before touching any data.
            with tempfile.TemporaryDirectory(prefix="cricsheet_") as tmp:
                zip_path = Path(tmp) / "npl_json.zip"
                try:
                    urllib.request.urlretrieve(BUNDLE_URL, zip_path)
                    with zipfile.ZipFile(zip_path) as zf:
                        bad = zf.testzip()
                        names = [n for n in zf.namelist() if n.endswith(".json")]
                        if bad is not None or not names:
                            raise ValueError(f"corrupt bundle (bad={bad})")
                        zf.extractall(Path(tmp) / "npl_json")
                except Exception as exc:  # download/verify failure: abort clean
                    print(f"STATUS FAIL: bundle download/verify failed: {exc}")
                    log.write(f"download failed: {exc}\n")
                    return 1
                print(f"bundle: {len(names)} match JSONs")
                log.write(f"bundle json files: {len(names)}\n")

                # 2. Ingest (idempotent append).
                if not run_step(
                    "ingest",
                    [py, "scripts/ingest_cricsheet.py",
                     str(Path(tmp) / "npl_json"), "--append"],
                    log,
                ):
                    print(f"STATUS FAIL: ingest step failed; see {log_path}")
                    return 1

            # 3. Rebuild derived data.
            if not run_step("normalize", [py, "-m", "src.preprocessing.normalize_data"], log):
                print(f"STATUS FAIL: normalize step failed; see {log_path}")
                return 1
            if not run_step("refresh", [py, "refresh_all.py"], log):
                print(f"STATUS FAIL: refresh_all step failed; see {log_path}")
                return 1

            m1, d1, ids1 = parquet_counts()
            fresh = ids1 - ids0
            print(f"matches: {m0} -> {m1} (new: {len(fresh)})")
            print(f"deliveries: {d0} -> {d1} (added: {d1 - d0})")
            for line in new_match_lines(fresh):
                print(line)
            print(f"STATUS OK: {len(fresh)} new match(es); log {log_path}")
            return 0
    finally:
        LOCK.unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main())
