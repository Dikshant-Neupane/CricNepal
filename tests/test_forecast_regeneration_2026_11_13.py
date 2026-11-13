"""Pin: the shipped S3 forecasts reproduce from the current forecaster.

The shipped s3_bowler_forecast.csv / s3_batter_forecast.csv used to
pre-date the bcad4f1 trend-order fix and the v2.2 confidence-interval
formula, with no live script to regenerate them (bug found in the
2026-11-13 sweep). scripts/regenerate_s3_forecasts.py is now the
pinned writer; this test fails if the shipped files drift from what
that script produces, so any forecaster or roster change must come
with a regeneration, not a silent drift.
"""

import importlib.util
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent


def _load_regen_script():
    path = ROOT / "scripts" / "regenerate_s3_forecasts.py"
    spec = importlib.util.spec_from_file_location("regen_s3_forecasts", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def fresh_forecasts():
    from src.analytics.s3_performance_forecaster import S3PerformanceForecaster

    regen = _load_regen_script()
    s1, s2 = regen.load_and_prepare_data()
    fc = S3PerformanceForecaster(s1, s2)
    return {
        "bowlers": fc.forecast_bowlers().sort_values("player_name").reset_index(drop=True),
        "batters": fc.forecast_batters().sort_values("player_name").reset_index(drop=True),
    }


def _assert_frames_equal(fresh: pd.DataFrame, shipped_path: Path):
    """Fresh forecaster output must match the shipped CSV.

    Numeric columns compare with a 1e-9 tolerance: pandas' CSV float
    formatting changed between versions (in-memory
    10.709999999999999 vs shipped "10.71" are the same value at
    display precision), so a string comparison would fail on
    formatting alone. String columns compare exactly.
    """
    import numpy as np

    shipped = pd.read_csv(shipped_path).sort_values("player_name").reset_index(drop=True)
    assert list(fresh.columns) == list(shipped.columns), "column mismatch"
    assert len(fresh) == len(shipped), "row count mismatch"
    for col in fresh.columns:
        a, b = fresh[col], shipped[col]
        if pd.api.types.is_numeric_dtype(a) and pd.api.types.is_numeric_dtype(b):
            assert np.allclose(
                a.to_numpy(dtype=float), b.to_numpy(dtype=float), rtol=0, atol=1e-9, equal_nan=True
            ), f"col {col}: numeric mismatch"
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                if pd.isna(x) and pd.isna(y):
                    continue
                assert str(x) == str(y), f"row {i} col {col}: fresh {x!r} != shipped {y!r}"


def test_bowler_forecast_reproduces(fresh_forecasts):
    _assert_frames_equal(
        fresh_forecasts["bowlers"], ROOT / "data" / "exports" / "s3_bowler_forecast.csv"
    )


def test_batter_forecast_reproduces(fresh_forecasts):
    _assert_frames_equal(
        fresh_forecasts["batters"], ROOT / "data" / "exports" / "s3_batter_forecast.csv"
    )


def test_grade_files_reproduce(fresh_forecasts):
    for grade in ("Grade A", "Grade B", "Grade C"):
        subset = fresh_forecasts["bowlers"][
            fresh_forecasts["bowlers"]["npl_grade"].str.contains(grade, na=False)
        ].sort_values("priority", ascending=False)
        _assert_frames_equal(
            subset.sort_values("player_name").reset_index(drop=True),
            ROOT / "data" / "exports" / f"NPL_Grade_{grade.split()[-1]}_Targets.csv",
        )
