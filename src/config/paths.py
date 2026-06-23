"""
Central path configuration for CricNepal project.

All data paths are resolved from environment variables with sensible defaults.
This ensures the project runs on any machine without hardcoded paths.

Environment Variables:
    CRIC_DATA_DIR   — Root of external cricket data (parquet files, rosters)
                      Default: D:/Cric_Data/data
    CRICNEPAL_ROOT  — Project root (auto-detected if unset)
"""

import os
from pathlib import Path


def _project_root() -> Path:
    """Detect project root (3 levels up from this file: src/config/paths.py)."""
    return Path(__file__).resolve().parent.parent.parent


# ── Project paths ────────────────────────────────────────────
PROJECT_ROOT = Path(os.environ.get("CRICNEPAL_ROOT", str(_project_root())))
DATA_DIR = PROJECT_ROOT / "data"
NORMALIZED_DIR = DATA_DIR / "normalized"
EXPORT_DIR = DATA_DIR / "exports"
RAW_DIR = DATA_DIR / "raw"
DELIVERABLES_DIR = PROJECT_ROOT / "deliverables"

# ── External data paths ─────────────────────────────────────
_cric_data_default = str(PROJECT_ROOT.parent / "Cric_Data" / "data")
CRIC_DATA_DIR = Path(os.environ.get("CRIC_DATA_DIR", _cric_data_default))

if not CRIC_DATA_DIR.exists():
    # If external Cric_Data is missing (e.g. in Streamlit Cloud),
    # fall back to the bundled production_assets directory first.
    _production_assets = DATA_DIR / "production_assets"
    if _production_assets.exists():
        CRIC_DATA_DIR = _production_assets
    else:
        CRIC_DATA_DIR = DATA_DIR
    
PARQUET_DIR = CRIC_DATA_DIR / "final" / "parquet"
ROSTER_DIR = CRIC_DATA_DIR / "player_rosters"
PROFILES_DIR = CRIC_DATA_DIR / "player_profiles"


def ensure_dirs() -> None:
    """Create output directories if they don't exist."""
    for d in [DATA_DIR, NORMALIZED_DIR, EXPORT_DIR, DELIVERABLES_DIR]:
        d.mkdir(parents=True, exist_ok=True)
