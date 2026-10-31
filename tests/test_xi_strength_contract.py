"""Plan task 4.1 (criteria D5, V1): predict_fixture must pass the FULL
selected XI into xi_strength, counting players without a cricsheet
registry ID via the priors table by player_key (their index is
whatever the priors say -- exactly 1.0 for debutants), per
model.xi_strength's documented contract. The pre-fix code mapped the
XI through reg_ids() and DROPPED no-ID players, shrinking the mean's
denominator.

Audit-figure note: the audit's full-mean Biratnagar figure (1.0274)
reproduces exactly on the branch's data and is pinned below. The
audit's dropped-mean figure (1.0430) could NOT be reproduced from the
branch's current priors, expected XIs or locked upcoming predictions
(no current XI contains a no-ID player, so no current number
changes); the distortion is pinned synthetically instead, where it
is demonstrable.
"""
from pathlib import Path

import pandas as pd
import pytest

from src.prediction import engine

ROOT = Path(__file__).resolve().parent.parent
PRED = ROOT / "data" / "predictions"


def _priors_by_key(rows):
    return {r["player_key"]: r for r in rows}


def test_predict_fixture_counts_no_id_players_by_key():
    # Team A: 10 players with IDs at bat 1.20 + 1 no-ID player at 0.90.
    # Full-mean = (10*1.20 + 0.90)/11 = 1.1727. The dropped-mean the old
    # code produced = 1.20.
    rows_a = [dict(player_key=f"a{i}", cricsheet_registry_id=f"id_a{i}",
                   bat_index=1.20, bowl_index=1.0) for i in range(10)]
    rows_a.append(dict(player_key="a_noid", cricsheet_registry_id=None,
                       bat_index=0.90, bowl_index=1.0))
    rows_b = [dict(player_key=f"b{i}", cricsheet_registry_id=f"id_b{i}",
                   bat_index=1.0, bowl_index=1.0) for i in range(11)]
    pbk = _priors_by_key(rows_a + rows_b)
    xi = {"A": [r["player_key"] for r in rows_a],
          "B": [r["player_key"] for r in rows_b]}
    pred = engine.predict_fixture(
        "A", "B", "2026-11-01", {"A": 1500.0, "B": 1500.0}, pbk, xi,
        {"A": 0.0, "B": 0.0}, {}, None)
    expected = (10 * 1.20 + 0.90) / 11 - 1.0
    assert pred["features"]["xi_batting_diff"] == pytest.approx(expected)
    assert pred["features"]["xi_batting_diff"] != pytest.approx(0.20)


def test_biratnagar_full_mean_regression():
    priors = pd.read_csv(PRED / "player_priors.csv")
    pbk = {r.player_key: r._asdict() for r in priors.itertuples()}
    squad = priors[priors.team == "Biratnagar Kings"]
    xi = engine.select_expected_xi(squad)
    from src.prediction import model as M
    bat, _ = M.xi_strength(xi, pbk)
    assert bat == pytest.approx(1.0274, abs=1e-4)
