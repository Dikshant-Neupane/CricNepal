"""Pin: analytics modules load ball-by-ball data on a fresh clone.

data/normalized/ball_by_ball_normalized.parquet is not in the repo
(untracked; *.parquet is gitignored), so every direct read of it
crashed with FileNotFoundError — failing-before on this box, where
the file is absent. The modules now share
src.config.paths.resolve_ball_by_ball_parquet(), which falls back
to data/final/parquet/ball_by_ball.parquet (the same projection the
dashboard loaders and scripts/prepare_season_features.py already
use, audit A7). These tests fail if any module goes back to reading
the normalized path directly.
"""

from pathlib import Path

import pandas as pd
import pytest

import src.config.paths as paths

ROOT = Path(__file__).resolve().parent.parent

ANALYTICS_MODULES = [
    "captaincy_analysis.py",
    "death_batting_two_tier_analysis.py",
    "death_bowling_two_tier_analysis.py",
    "league_dew_factor_analysis.py",
    "middle_overs_analysis.py",
    "player_attribution_analysis.py",
    "player_clustering.py",
    "powerplay_analysis.py",
    "root_cause_analysis.py",
    "tactical_audit.py",
    "win_probability_model.py",
]


class TestResolver:
    def test_falls_back_to_final_parquet_when_normalized_missing(self):
        """On this box the normalized file is absent; the resolver
        must return the shipped final parquet."""
        assert not (paths.NORMALIZED_DIR / "ball_by_ball_normalized.parquet").exists()
        resolved = paths.resolve_ball_by_ball_parquet()
        assert resolved == paths.PARQUET_DIR / "ball_by_ball.parquet"
        assert resolved.exists()

    def test_prefers_canonical_when_present(self, tmp_path, monkeypatch):
        canonical_dir = tmp_path / "normalized"
        fallback_dir = tmp_path / "final" / "parquet"
        canonical_dir.mkdir(parents=True)
        fallback_dir.mkdir(parents=True)
        (canonical_dir / "ball_by_ball_normalized.parquet").touch()
        (fallback_dir / "ball_by_ball.parquet").touch()
        monkeypatch.setattr(paths, "NORMALIZED_DIR", canonical_dir)
        monkeypatch.setattr(paths, "PARQUET_DIR", fallback_dir)
        assert paths.resolve_ball_by_ball_parquet() == (
            canonical_dir / "ball_by_ball_normalized.parquet"
        )

    def test_raises_naming_both_candidates_when_neither_exists(self, tmp_path, monkeypatch):
        monkeypatch.setattr(paths, "NORMALIZED_DIR", tmp_path / "normalized")
        monkeypatch.setattr(paths, "PARQUET_DIR", tmp_path / "final" / "parquet")
        with pytest.raises(FileNotFoundError, match="ball-by-ball parquet not found"):
            paths.resolve_ball_by_ball_parquet()


class TestModuleWiring:
    @pytest.mark.parametrize("module", ANALYTICS_MODULES)
    def test_module_uses_resolver_not_direct_path(self, module):
        text = (ROOT / "src" / "analytics" / module).read_text()
        assert "resolve_ball_by_ball_parquet" in text, module
        assert 'read_parquet(NORMALIZED_DIR / "ball_by_ball_normalized.parquet")' not in text, module
        assert 'read_parquet(DATA_DIR / "ball_by_ball_normalized.parquet")' not in text, module
        assert "DELIVERIES_FILE" not in text, module


class TestLoadersReturnRealRows:
    """Loader functions that used to crash now return the 17,553-row frame."""

    def test_captaincy_load_data(self):
        from src.analytics.captaincy_analysis import load_data

        bbb, matches = load_data()
        assert len(bbb) == 17553
        assert len(matches) == 76

    def test_death_batting_loader(self):
        from src.analytics.death_batting_two_tier_analysis import load_ball_by_ball

        assert len(load_ball_by_ball()) == 17553

    def test_death_bowling_loader(self):
        from src.analytics.death_bowling_two_tier_analysis import load_ball_by_ball

        assert len(load_ball_by_ball()) == 17553

    def test_dew_load_data(self):
        from src.analytics.league_dew_factor_analysis import load_data

        bbb, matches = load_data()
        assert len(bbb) == 17553
        assert len(matches) == 76

    def test_middle_overs_loader(self):
        from src.analytics.middle_overs_analysis import load_ball_by_ball

        assert len(load_ball_by_ball()) == 17553

    def test_powerplay_loader(self):
        from src.analytics.powerplay_analysis import load_ball_by_ball

        assert len(load_ball_by_ball()) == 17553

    def test_root_cause_loader(self):
        from src.analytics.root_cause_analysis import load_janakpur_matches

        matches, bbb = load_janakpur_matches()
        assert len(bbb) > 0
        assert set(bbb["batting_team"].unique()) | set(bbb["bowling_team"].unique()) >= {
            "Janakpur Bolts"
        }

    def test_attribution_loader(self):
        from src.analytics.player_attribution_analysis import load_janakpur_data

        matches, deliveries = load_janakpur_data()
        assert len(deliveries) > 0
        assert len(matches) > 0

    def test_win_probability_pipeline_passes_data_guard(self, monkeypatch):
        """compute_and_export_wpa_oos used to return early here: its
        guard required the normalized file, which is absent on a fresh
        clone. With the resolver it must reach predict_walk_forward.
        The walk-forward itself is stubbed out so this test writes
        nothing."""
        import src.analytics.win_probability_model as wpm

        called = {}

        def fake_predict(deliveries, matches, min_train_matches=4):
            called["predict"] = True
            return pd.DataFrame()

        monkeypatch.setattr(wpm, "predict_walk_forward", fake_predict)
        wpm.compute_and_export_wpa_oos()
        assert called.get("predict") is True
