"""Tests for the dashboard / pipeline bugs fixed in the 2026-11-13 sweep.

Each test pins a bug found by the whole-project sweep, with the
failing-before behaviour recorded in its docstring.
"""

import ast
import json
import math
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent

from src.dashboard.page_modules.settings_page import provisional_summary
from src.dashboard.page_modules.s3_strategic_analysis import format_economy


class TestProvisionalSummary:
    """Settings page provisional counts (bug 1)."""

    def test_flat_keys_from_real_status_file(self):
        """The live file says 8 recorded / 12 superseded.

        Failing-before: the page read status.get("provisional", {})
        and rendered "0 recorded (superseded: 0)" — the file has no
        "provisional" object, only flat keys.
        """
        status = json.loads((ROOT / "data" / "predictions" / "predictions_status.json").read_text())
        assert provisional_summary(status) == (8, 12)

    def test_missing_keys_default_to_zero(self):
        assert provisional_summary({}) == (0, 0)
        assert provisional_summary({"n_provisional": 3}) == (3, 0)


class TestFormatEconomy:
    """S3 strategic analysis Death banner (bug 2)."""

    def test_nan_never_prints_as_nan(self):
        """Failing-before: f"{nan:.2f}" printed "S2 Economy: nan"."""
        assert format_economy(float("nan")) != "nan"
        assert "nan" not in format_economy(float("nan")).lower()

    def test_normal_value_formats_to_two_decimals(self):
        assert format_economy(6.0) == "6.00"
        assert format_economy(10.67) == "10.67"

    def test_top_death_bowler_banner_value(self):
        """The current top Death bowler has no S2 balls, so the banner
        value must not be NaN text. (Legal-ball switch 2026-11-13:
        his projection moved 7.39 -> 7.53, so the old < 7.5 cutoff
        no longer catches him; select by sort, not a threshold.)"""
        df = pd.read_csv(ROOT / "data" / "exports" / "s3_phase_bowler_forecast.csv")
        death = df[df["phase"].str.lower() == "death"].sort_values("s3_economy_proj")
        top = death.iloc[0]
        assert top["bowler_name"] == "Saad Bin Zafar"
        assert math.isnan(top["s2_economy_raw"])
        assert "nan" not in format_economy(top["s2_economy_raw"]).lower()


class TestPipelineWiring:
    """refresh_all.py must regenerate the pinned S3 exports (bug 3)."""

    @staticmethod
    def _pipeline_steps():
        tree = ast.parse((ROOT / "refresh_all.py").read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "PIPELINE_STEPS":
                return ast.literal_eval(node.value)
        raise AssertionError("PIPELINE_STEPS not found in refresh_all.py")

    def test_phase_forecast_regenerator_is_a_step(self):
        steps = self._pipeline_steps()
        scripts = [script for _, script in steps]
        assert "scripts/regenerate_s3_bowler_forecast.py" in scripts

    def test_forecast_regenerator_is_a_step(self):
        steps = self._pipeline_steps()
        scripts = [script for _, script in steps]
        assert "scripts/regenerate_s3_forecasts.py" in scripts

    def test_every_step_script_exists(self):
        for name, script in self._pipeline_steps():
            assert (ROOT / script).exists(), f"pipeline step {name!r} points at missing {script}"


class TestGenerateChartsPaths:
    """generate_charts.py Windows paths (bug 6)."""

    def test_paths_are_repo_relative(self):
        """Failing-before: DATA_DIR was Path("D:/CricNepal/data/exports"),
        a relative path on Linux that also created a literal "D:"
        directory in the cwd at import time."""
        import src.visualizations.generate_charts as charts

        assert "D:" not in str(charts.DATA_DIR)
        assert "D:" not in str(charts.OUTPUT_DIR)
        assert charts.DATA_DIR.is_absolute()
        assert charts.OUTPUT_DIR.is_absolute()
        assert charts.DATA_DIR == ROOT / "data" / "exports"
        assert charts.OUTPUT_DIR == ROOT / "docs" / "visualizations"
        assert (charts.DATA_DIR / "player_death_bowlers_deltas.csv").exists()


class TestRecruitingWarningText:
    """s3_recruiting.py warning names the wrong source (bug 7)."""

    def test_warning_names_the_real_inputs(self):
        text = (ROOT / "src" / "dashboard" / "page_modules" / "s3_recruiting.py").read_text()
        assert "ball_by_ball_normalized" not in text
        assert "player_innings.parquet" in text
        assert "matches.parquet" in text
