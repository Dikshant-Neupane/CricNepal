#!/usr/bin/env python
"""Build (or verify) the frozen-log ledger manifest.

The manifest is the reproducibility record for the locked Season 3
forecasts (review §9.1): it pins the code state and the exact input
snapshots that drove the locks, so any later claim about a locked
prediction can be checked against the artefacts that produced it.

Contents (data/predictions/ledger_manifest.json):
  - generated_at (UTC)
  - git HEAD SHA of this repo, plus an honest dirty-tree statement:
    the list of modified TRACKED files under src/ and scripts/ (and
    untracked files there), so the manifest never pretends the code
    matches the SHA when the working tree has moved on.
  - the frozen log itself: SHA-256, row count, and per locked stage:
    row count, first/last lock timestamps, model version(s).
  - SHA-256 of every input snapshot that drove the locks (fixtures,
    player master, priors, cross-league history, pre-registration).

--verify recomputes everything from the current tree and reports
MATCH / MISMATCH per entry against the stored manifest (exit 1 on any
mismatch). The dirty-tree listing and generated_at are state of the
moment and are reported for information, not verified.

Future lock events should regenerate this manifest;
scripts/lock_matchday.py does so automatically after a successful
lock (best-effort: a manifest failure never blocks a lock).
"""
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
FROZEN_LOG = "data/predictions/frozen_log.csv"
SNAPSHOTS = [
    "data/fixtures/s3_fixtures.csv",
    "data/predictions/player_master.csv",
    "data/predictions/player_priors.csv",
    "data/predictions/player_history.csv",
    "data/predictions/preregistration_s3.json",
]
MANIFEST_PATH = ROOT / "data/predictions/ledger_manifest.json"
CODE_DIRS = ("src/", "scripts/")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git(root: Path, *args) -> str:
    return subprocess.run(["git", *args], cwd=root, capture_output=True,
                          text=True, check=True).stdout


def git_state(root: Path = ROOT) -> dict:
    head = _git(root, "rev-parse", "HEAD").strip()
    modified, untracked = [], []
    for line in _git(root, "status", "--porcelain", "--", *CODE_DIRS).splitlines():
        if not line.strip():
            continue
        status, path = line[:2], line[3:].strip()
        (untracked if status == "??" else modified).append(path)
    return {"head_sha": head,
            "dirty_code_tree": bool(modified or untracked),
            "modified_tracked_files": sorted(modified),
            "untracked_files": sorted(untracked)}


def stage_summary(log: pd.DataFrame) -> dict:
    out = {}
    for stage, g in log.groupby("stage"):
        out[str(stage)] = {
            "rows": int(len(g)),
            "first_locked": str(g["timestamp_locked"].min()),
            "last_locked": str(g["timestamp_locked"].max()),
            "model_versions": sorted(str(v) for v in g["model_version"].unique()),
        }
    return out


def build_manifest(root: Path = ROOT) -> dict:
    log_path = root / FROZEN_LOG
    log = pd.read_csv(log_path)
    snapshots = {}
    for rel in SNAPSHOTS:
        p = root / rel
        snapshots[rel] = ({"sha256": sha256_file(p), "bytes": p.stat().st_size}
                          if p.exists() else {"sha256": None, "bytes": None,
                                              "missing": True})
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git": git_state(root),
        "frozen_log": {"path": FROZEN_LOG, "sha256": sha256_file(log_path),
                       "rows": int(len(log)), "stages": stage_summary(log)},
        "input_snapshots": snapshots,
        "note": ("Regenerate after every future lock event "
                 "(scripts/lock_matchday.py does this automatically). "
                 "Verify with: python scripts/build_ledger_manifest.py --verify"),
    }


def verify_manifest(root: Path = ROOT) -> tuple[list, bool]:
    """Returns (report lines, all_match)."""
    manifest_path = root / "data/predictions/ledger_manifest.json"
    if not manifest_path.exists():
        return ["ledger_manifest.json: MISSING (run without --verify first)"], False
    stored = json.loads(manifest_path.read_text())
    current = build_manifest(root)
    lines, ok = [], True

    def check(label, a, b):
        nonlocal ok
        match = a == b
        ok = ok and match
        lines.append(f"{label}: {'MATCH' if match else 'MISMATCH'}"
                     + ("" if match else f" (manifest={a!r} current={b!r})"))

    check("git.head_sha", stored["git"]["head_sha"], current["git"]["head_sha"])
    check("frozen_log.sha256", stored["frozen_log"]["sha256"],
          current["frozen_log"]["sha256"])
    check("frozen_log.rows", stored["frozen_log"]["rows"],
          current["frozen_log"]["rows"])
    stages = sorted(set(stored["frozen_log"]["stages"])
                    | set(current["frozen_log"]["stages"]))
    for stage in stages:
        check(f"stage[{stage}]", stored["frozen_log"]["stages"].get(stage),
              current["frozen_log"]["stages"].get(stage))
    for rel in SNAPSHOTS:
        check(f"snapshot[{rel}]",
              stored["input_snapshots"].get(rel, {}).get("sha256"),
              current["input_snapshots"].get(rel, {}).get("sha256"))
    lines.append(f"git.dirty_code_tree (info only): "
                 f"current={current['git']['dirty_code_tree']}, "
                 f"modified={current['git']['modified_tracked_files']}")
    return lines, ok


def main() -> int:
    if "--verify" in sys.argv:
        lines, ok = verify_manifest()
        for line in lines:
            print(line)
        print("LEDGER VERIFY:", "ALL MATCH" if ok else "MISMATCH FOUND")
        return 0 if ok else 1
    manifest = build_manifest()
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=1))
    print(f"manifest -> {MANIFEST_PATH}")
    print(f"  git HEAD {manifest['git']['head_sha'][:12]} "
          f"dirty_code_tree={manifest['git']['dirty_code_tree']}")
    print(f"  frozen log rows={manifest['frozen_log']['rows']} "
          f"sha256={manifest['frozen_log']['sha256'][:16]}...")
    for stage, s in manifest["frozen_log"]["stages"].items():
        print(f"  stage {stage}: {s['rows']} rows, "
              f"{s['first_locked']} .. {s['last_locked']}, "
              f"versions={s['model_versions']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
