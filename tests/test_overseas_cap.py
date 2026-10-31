"""Plan task 3.1 (criteria E2, E3): the NPL playing conditions
(docs/PLAYING_CONDITIONS.md, REPORTED-CORROBORATED) allow at most 4
overseas players in a playing XI.

Pins:
- select_expected_xi repairs an over-cap XI down to 4 overseas,
  swapping overseas -> domestic only, and leaves every already-legal
  team's XI byte-for-byte identical to the pre-fix selector
  (tests/pinned_expected_xi_prefix.json, generated from the pre-fix
  code on the branch's priors).
- A squad frame without the is_overseas column is refused loudly --
  the cap must never be silently skipped.
- lock_matchday.validate_xi rejects an announced XI with 5 overseas
  (reason shown) and returns a legal XI unchanged.
"""
import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest

from src.prediction import engine

ROOT = Path(__file__).resolve().parent.parent
PRED = ROOT / "data" / "predictions"
PINNED = json.loads((ROOT / "tests" / "pinned_expected_xi_prefix.json")
                    .read_text())


def _lock_matchday():
    spec = importlib.util.spec_from_file_location(
        "lock_matchday", ROOT / "scripts/lock_matchday.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _synthetic_squad():
    """13 players; the unconstrained top 11 contains 6 overseas."""
    rows = []
    for i, bat in enumerate([1.30, 1.28, 1.26, 1.24, 1.22, 1.20], start=1):
        rows.append(dict(player_key=f"os_bat{i}", role="Batter",
                         bat_index=bat, bowl_index=1.0, bat_balls_eff=500.0,
                         bowl_balls_eff=100.0, is_overseas=True))
    rows += [
        dict(player_key="dom_bowl", role="Bowler", bat_index=1.0,
             bowl_index=1.30, bat_balls_eff=100.0, bowl_balls_eff=500.0,
             is_overseas=False),
        dict(player_key="dom_bat1", role="Batter", bat_index=1.15,
             bowl_index=1.0, bat_balls_eff=500.0, bowl_balls_eff=100.0,
             is_overseas=False),
        dict(player_key="dom_ar", role="All-rounder", bat_index=1.10,
             bowl_index=1.10, bat_balls_eff=300.0, bowl_balls_eff=300.0,
             is_overseas=False),
        dict(player_key="dom_wk", role="Wicketkeeper", bat_index=1.10,
             bowl_index=1.0, bat_balls_eff=500.0, bowl_balls_eff=100.0,
             is_overseas=False),
        dict(player_key="dom_bat2", role="Batter", bat_index=1.12,
             bowl_index=1.0, bat_balls_eff=500.0, bowl_balls_eff=100.0,
             is_overseas=False),
        dict(player_key="dom_bat3", role="Batter", bat_index=1.05,
             bowl_index=1.0, bat_balls_eff=500.0, bowl_balls_eff=100.0,
             is_overseas=False),
        dict(player_key="dom_bat4", role="Batter", bat_index=1.02,
             bowl_index=1.0, bat_balls_eff=500.0, bowl_balls_eff=100.0,
             is_overseas=False),
    ]
    return pd.DataFrame(rows)


def test_selector_repairs_over_cap_xi():
    squad = _synthetic_squad()
    xi = engine.select_expected_xi(squad)
    assert len(xi) == 11 and len(set(xi)) == 11
    os_in = [k for k in xi if k.startswith("os_")]
    assert len(os_in) == 4
    # the two lowest-scored overseas players are the ones swapped out,
    # replaced by the best remaining domestic players
    assert "os_bat5" not in xi and "os_bat6" not in xi
    assert "dom_bat3" in xi and "dom_bat4" in xi
    rows = squad[squad.player_key.isin(xi)]
    assert (rows.role == "Wicketkeeper").sum() >= 1


def test_selector_refuses_squad_without_overseas_flag():
    squad = _synthetic_squad().drop(columns=["is_overseas"])
    with pytest.raises(ValueError, match="is_overseas"):
        engine.select_expected_xi(squad)


def test_selector_refuses_unknown_overseas_flags():
    # e.g. priors built from a master without overseas data (the S2
    # backtest's synthetic master): NaN must never be read as a bool.
    squad = _synthetic_squad().astype({"is_overseas": object})
    squad.loc[0, "is_overseas"] = None
    with pytest.raises(ValueError, match="is_overseas"):
        engine.select_expected_xi(squad)


def test_real_xis_legal_teams_unchanged_violators_minimally_repaired():
    priors = pd.read_csv(PRED / "player_priors.csv")
    master = pd.read_csv(PRED / "player_master.csv")
    overseas = dict(zip(master.player_key, master.is_overseas))
    for team, squad in priors.groupby("team"):
        xi = engine.select_expected_xi(squad)
        assert len(xi) == 11 and len(set(xi)) == 11
        nos = sum(1 for k in xi if overseas[k])
        assert nos <= 4, f"{team}: {nos} overseas after repair"
        rows = squad[squad.player_key.isin(xi)]
        if (squad.role == "Wicketkeeper").any():
            assert (rows.role == "Wicketkeeper").sum() >= 1
        pinned = PINNED[team]
        if pinned["overseas"] <= 4:
            assert xi == pinned["xi"], f"{team}: legal XI was altered"
        else:
            removed = [k for k in pinned["xi"] if k not in xi]
            added = [k for k in xi if k not in pinned["xi"]]
            assert len(removed) == len(added) == pinned["overseas"] - 4
            assert all(overseas[k] for k in removed)
            assert all(not overseas[k] for k in added)


def _master_and_fixture(n_os_team_x=5):
    master_rows = []
    for i in range(1, 12):
        master_rows.append(dict(player_key=f"x{i}", team="Team X",
                                is_overseas=i <= n_os_team_x))
    for i in range(1, 12):
        master_rows.append(dict(player_key=f"y{i}", team="Team Y",
                                is_overseas=False))
    master = pd.DataFrame(master_rows)
    fixture = pd.Series({"team_1_name": "Team X", "team_2_name": "Team Y"})
    xi_rows = []
    for team, prefix in (("Team X", "x"), ("Team Y", "y")):
        for pos in range(1, 12):
            # validate_xi consumes the RESOLVED frame (player_key set
            # by resolve_players in the real flow)
            xi_rows.append(dict(team=team, player=f"{prefix}{pos}",
                                player_key=f"{prefix}{pos}",
                                batting_position=pos))
    return master, fixture, pd.DataFrame(xi_rows)


def test_validate_xi_rejects_five_overseas_with_reason():
    lm = _lock_matchday()
    master, fixture, xi = _master_and_fixture(n_os_team_x=5)
    with pytest.raises(ValueError, match="overseas"):
        lm.validate_xi(xi, fixture, master)


def test_validate_xi_legal_xi_returned_unchanged():
    lm = _lock_matchday()
    master, fixture, xi = _master_and_fixture(n_os_team_x=4)
    out = lm.validate_xi(xi, fixture, master)
    assert out == {"Team X": [f"x{i}" for i in range(1, 12)],
                   "Team Y": [f"y{i}" for i in range(1, 12)]}
