"""
pytest configuration file
Adds project root to Python path for imports
"""
import sys
from pathlib import Path

import pytest

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def _missing_real_dataset_files() -> bool:
    """
    These tests expect the production normalized parquet files to exist.
    In some environments (CI/dev boxes) the dataset is not present.
    """
    matches_parquet = project_root / "data" / "normalized" / "matches_normalized.parquet"
    return not matches_parquet.exists()


def pytest_collection_modifyitems(config, items):
    """
    Skip real-dataset tests when the required parquet files are not available.
    """
    if not _missing_real_dataset_files():
        return

    skip = pytest.mark.skip(reason="Real normalized parquet dataset not available in this environment")

    for item in items:
        # Only skip tests that require the real parquet.
        # (Keeps unit tests running even without data/)
        nodeid = item.nodeid
        if (
            "test_opposition_strength_analysis.py" in nodeid
            or "test_normalize_scorecard.py" in nodeid
        ):
            item.add_marker(skip)
