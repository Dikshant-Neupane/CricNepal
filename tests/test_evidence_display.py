"""Plan 6.1 — evidence context on the live Game Plan prior tables (S1, B2).

The phase-prior tables showed bare indices. They now also carry the
effective balls behind each estimate, the prior group as the evidence
label, and the prior uncertainty, with a legend at the render site.
No displayed number changes: the pre-existing columns and values are
pinned by the first test.
"""
import pandas as pd
import pytest

import src.dashboard.page_modules.game_plan as gp


def _priors() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "player_key": "p1", "canonical_name": "Player One",
            "team": "Janakpur Bolts", "role": "Batter", "is_overseas": False,
            "bat_index": 1.20, "bowl_index": 0.90,
            "prior_bat_rpb_powerplay": 1.10, "prior_bat_rpb_middle": 1.20,
            "prior_bat_rpb_death": 1.40,
            "prior_bowl_econ_powerplay": 7.0, "prior_bowl_econ_middle": 7.5,
            "prior_bowl_econ_death": 8.5,
            "bat_balls_eff": 321.5, "bowl_balls_eff": 88.0,
            "prior_group": "npl_experienced", "uncertainty": 0.42,
        },
        {
            "player_key": "p2", "canonical_name": "Player Two",
            "team": "Janakpur Bolts", "role": "Bowler", "is_overseas": True,
            "bat_index": 0.95, "bowl_index": 1.10,
            "prior_bat_rpb_powerplay": 0.90, "prior_bat_rpb_middle": 0.95,
            "prior_bat_rpb_death": 1.00,
            "prior_bowl_econ_powerplay": 6.5, "prior_bowl_econ_middle": 7.0,
            "prior_bowl_econ_death": 8.0,
            "bat_balls_eff": 40.0, "bowl_balls_eff": 210.0,
            "prior_group": "external_pro", "uncertainty": 0.95,
        },
    ])


def test_existing_numbers_unchanged() -> None:
    tables = gp._team_tables(_priors(), "Janakpur Bolts")
    bat = tables["bat"]
    assert bat.iloc[0]["Player"] == "Player One"
    assert bat.iloc[0]["Bat idx"] == pytest.approx(1.20)
    assert bat.iloc[0]["PP"] == pytest.approx(1.10)
    bowl = tables["bowl"]
    assert bowl.iloc[0]["Player"] == "Player Two"
    assert bowl.iloc[0]["Bowl idx"] == pytest.approx(1.10)


def test_evidence_columns_present_with_source_values() -> None:
    tables = gp._team_tables(_priors(), "Janakpur Bolts")
    bat = tables["bat"].set_index("Player")
    assert bat.loc["Player One", "Bat balls (eff)"] == pytest.approx(321.5)
    assert bat.loc["Player One", "Evidence"] == "npl_experienced"
    assert bat.loc["Player One", "±"] == pytest.approx(0.42)
    bowl = tables["bowl"].set_index("Player")
    assert bowl.loc["Player Two", "Bowl balls (eff)"] == pytest.approx(210.0)
    assert bowl.loc["Player Two", "Evidence"] == "external_pro"
    assert bowl.loc["Player Two", "±"] == pytest.approx(0.95)


def test_fmt_table_keeps_evidence_label_as_text() -> None:
    tables = gp._team_tables(_priors(), "Janakpur Bolts")
    out = gp._fmt_table(tables["bat"])
    assert set(out["Evidence"]) == {"npl_experienced", "external_pro"}
    assert out.iloc[0]["Bat idx"] == "1.20"
