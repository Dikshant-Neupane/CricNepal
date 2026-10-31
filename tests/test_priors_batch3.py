"""Batch 3 priors tests (plan tasks 2.2, 6.2, and the is_overseas
column plan task 3.1 consumes).

2.2: "retired out" is NOT a bowler-credited dismissal (master prompt
Section 4; src/cricket/metrics.py BOWLER_CREDITED_WICKETS is the single
authority). A synthetic cricsheet match with one bowled and one
retired-out dismissal must credit the bowler with exactly 1 wicket.

6.2: compute_priors emits a documented posterior interval for the
batting runs/ball and bowling economy priors (normal partial-pooling:
sd = sqrt(mu / (n + k)) on the per-ball scale, x6 for economy), plus
the is_overseas flag carried from the master. New columns come LAST so
no positional consumer can be disturbed.
"""
import json
import zipfile
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from src.prediction import priors as P


def _synthetic_zip(tmp_path: Path) -> Path:
    """One T20I match: Bowler B bowls Batter A (bowled) and later
    Batter C retires out while B is bowling."""
    def dlv(batter, bowler, runs_batter=0, wicket=None):
        d = {"batter": batter, "bowler": bowler, "non_striker": "NS",
             "runs": {"batter": runs_batter, "extras": 0, "total": runs_batter}}
        if wicket:
            d["wickets"] = [wicket]
        return d
    match = {
        "info": {
            "dates": ["2025-06-01"],
            "registry": {"people": {"A": "id_a", "B": "id_b", "C": "id_c",
                                    "NS": "id_ns"}},
            "players": {"Team X": ["A", "C", "NS"], "Team Y": ["B"]},
            "teams": ["Team X", "Team Y"],
        },
        "innings": [{
            "team": "Team X",
            "overs": [{"over": 0, "deliveries": [
                dlv("A", "B", 0, {"kind": "bowled", "player_out": "A"}),
                dlv("C", "B", 1, {"kind": "retired out", "player_out": "C"}),
                dlv("NS", "B", 4),
            ]}],
        }],
    }
    zp = tmp_path / "t20s_json.zip"
    with zipfile.ZipFile(zp, "w") as z:
        z.writestr("9999999.json", json.dumps(match))
    return zp


def test_retired_out_is_not_bowler_credited(tmp_path):
    zp = _synthetic_zip(tmp_path)
    agg = P.aggregate_cricsheet({zp: "T20I"})
    b = agg[(agg.registry_id == "id_b") & (agg.phase == "ALL")]
    assert len(b) == 1
    # Aggregates are decay-weighted: the 2025-06-01 match carries
    # weight w per ball. 3 legal balls bowled, 5 runs conceded, and
    # exactly ONE bowler-credited wicket (the bowled; the retired out
    # must contribute 0).
    w = P._decay(date(2025, 6, 1))
    assert b.iloc[0]["bowl_balls"] == pytest.approx(3 * w)
    assert b.iloc[0]["bowl_runs"] == pytest.approx(5 * w)
    assert b.iloc[0]["bowl_wkts"] == pytest.approx(1 * w)


def test_bowler_wickets_set_matches_metrics_authority():
    from src.cricket.metrics import BOWLER_CREDITED_WICKETS
    assert set(P.BOWLER_WICKETS) == set(BOWLER_CREDITED_WICKETS)
    assert "retired out" not in P.BOWLER_WICKETS
    assert "run out" not in P.BOWLER_WICKETS


def _tiny_master_agg():
    """Two NPL batters with the same underlying rate but very
    different sample sizes, plus the league rows league_means needs."""
    agg = pd.DataFrame([
        # league volume so NPL means are well defined
        dict(registry_id="id_pool", competition="NPL", phase="ALL",
             bat_balls=10000.0, bat_runs=13000.0, dismissals=800.0,
             bowl_balls=10000.0, bowl_runs=13000.0, bowl_wkts=700.0),
        dict(registry_id="id_small", competition="NPL", phase="ALL",
             bat_balls=30.0, bat_runs=45.0, dismissals=2.0,
             bowl_balls=0.0, bowl_runs=0.0, bowl_wkts=0.0),
        dict(registry_id="id_big", competition="NPL", phase="ALL",
             bat_balls=3000.0, bat_runs=4500.0, dismissals=200.0,
             bowl_balls=0.0, bowl_runs=0.0, bowl_wkts=0.0),
    ])
    master = pd.DataFrame([
        dict(player_key="k_small", canonical_name="Small Sample",
             team="Team X", role="Batter", cricsheet_registry_id="id_small",
             is_overseas=False),
        dict(player_key="k_big", canonical_name="Big Sample",
             team="Team X", role="Batter", cricsheet_registry_id="id_big",
             is_overseas=True),
    ])
    return agg, master


def test_priors_carry_is_overseas_and_posterior_intervals():
    agg, master = _tiny_master_agg()
    out = P.compute_priors(agg, master)
    assert list(out["player_key"]) == ["k_small", "k_big"]
    # is_overseas carried through from the master, by player
    assert dict(zip(out.player_key, out.is_overseas)) == {
        "k_small": False, "k_big": True}
    # interval columns exist, bracket the point estimates, and are the
    # LAST columns in the frame (positional safety, plan 6.2)
    for lo, hi, est in (("bat_rpb_ci_lo", "bat_rpb_ci_hi", "prior_bat_rpb"),
                        ("bowl_econ_ci_lo", "bowl_econ_ci_hi", "prior_bowl_econ")):
        assert lo in out.columns and hi in out.columns
        assert (out[lo] <= out[est]).all() and (out[est] <= out[hi]).all()
    assert list(out.columns[-5:]) == ["is_overseas", "bat_rpb_ci_lo",
                                      "bat_rpb_ci_hi", "bowl_econ_ci_lo",
                                      "bowl_econ_ci_hi"]
    # the bigger sample earns the narrower interval (same raw rate)
    w = dict(zip(out.player_key, out.bat_rpb_ci_hi - out.bat_rpb_ci_lo))
    assert w["k_big"] < w["k_small"]
