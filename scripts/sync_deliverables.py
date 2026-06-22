"""
Sync canonical reports and exports into the deliverables/ folder.

The corrected versions of EXECUTIVE_BRIEF / FINAL_REPORT / LIMITATIONS /
METHODOLOGY_JOURNEY live at the project root. The `deliverables/` folder is
the snapshot we hand to outside readers. Without this script the two copies
drift, and stale numbers from before the off-by-one and extras-counting
fixes get circulated externally.

Run after any change to the root reports or a re-run of the analytics
modules that write into `data/exports/`.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

# Allow running as `python scripts/sync_deliverables.py` from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config.paths import DELIVERABLES_DIR, EXPORT_DIR, PROJECT_ROOT

REPORTS = [
    "EXECUTIVE_BRIEF.md",
    "FINAL_REPORT.md",
    "LIMITATIONS.md",
    "METHODOLOGY_JOURNEY.md",
    "README.md",
]


def _copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def sync_reports() -> int:
    n = 0
    for fname in REPORTS:
        src = PROJECT_ROOT / fname
        if not src.exists():
            continue
        dst = DELIVERABLES_DIR / fname
        _copy(src, dst)
        n += 1
    return n


def sync_data_exports() -> int:
    src_dir = EXPORT_DIR
    dst_dir = DELIVERABLES_DIR / "data_exports"
    if not src_dir.exists():
        return 0
    dst_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for src in src_dir.iterdir():
        if not src.is_file():
            continue
        _copy(src, dst_dir / src.name)
        n += 1
    return n


def main() -> None:
    n_reports = sync_reports()
    n_exports = sync_data_exports()
    print(f"Synced {n_reports} root reports → {DELIVERABLES_DIR}")
    print(f"Synced {n_exports} export files → {DELIVERABLES_DIR / 'data_exports'}")


if __name__ == "__main__":
    main()
