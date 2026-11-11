"""Plan task 3.3 (criterion E3): the simulator's bowler constraints
-- max 4 overs (24 balls) per bowler, no consecutive overs -- pinned
against the extracted _choose_bowler, plus a seeded end-to-end
regression proving the extraction changed no behaviour (inputs
pinned to the pre-corrections XIs so the plan-3.1 cap, which
legitimately changes Janakpur's XI, cannot leak into this check).
"""
import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest

from src.prediction import simulator as S

ROOT = Path(__file__).resolve().parent.parent


def _fixtures_module():
    spec = importlib.util.spec_from_file_location(
        "simulate_fixtures", ROOT / "scripts/simulate_fixtures.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_rotation_cycles_and_advances_pointer():
    active = ["A", "B", "C", "D", "E"]
    balls = {b: 0 for b in active}
    idx, seq = 0, []
    for _ in range(7):
        b, idx = S._choose_bowler(active, balls, idx)
        seq.append(b)
        balls[b] += 6
    assert seq == ["A", "B", "C", "D", "E", "A", "B"]


def test_quota_skips_exhausted_bowler():
    active = ["A", "B", "C"]
    balls = {"A": 24, "B": 0, "C": 0}
    b, _ = S._choose_bowler(active, balls, 0)
    assert b == "B"


def test_no_consecutive_overs_while_alternative_has_quota():
    active = ["A", "B", "C", "D", "E"]
    balls = {b: 0 for b in active}
    idx, prev = 0, None
    for _ in range(20):
        b, idx = S._choose_bowler(active, balls, idx)
        assert b != prev
        balls[b] += 6
        assert balls[b] <= 24
        prev = b


def test_all_at_quota_falls_back_to_first_bowler():
    active = ["A", "B", "C", "D"]
    balls = {b: 24 for b in active}
    b, idx = S._choose_bowler(active, balls, 2)
    assert b == "A" and idx == 2  # pointer unchanged on fallback


def test_seeded_match_regression_after_extraction():
    fx = _fixtures_module()
    ctx, dists, bowl_balls, priors_by_id = fx.build_sim_context(ROOT)
    pinned = json.loads((ROOT / "tests/pinned_expected_xi_prefix.json")
                        .read_text())
    xi_by_team = {t: v["xi"] for t, v in pinned.items()}
    t1, t2 = "Biratnagar Kings", "Janakpur Bolts"  # espn_1462596
    pbk = ctx["priors_by_key"]

    def xi_ids(team):
        out = []
        for k in xi_by_team[team]:
            rid = pbk[k].get("cricsheet_registry_id")
            out.append(rid if isinstance(rid, str) else f"key:{k}")
        return out

    xi1, xi2 = xi_ids(t1), xi_ids(t2)
    res = S.simulate_match(xi1, xi2,
                           fx.rotation(xi1, dists, bowl_balls),
                           fx.rotation(xi2, dists, bowl_balls),
                           dists, priors_by_id, n_sims=500, seed=3)
    # A/B-verified 2026-10-29: the PRE-extraction simulator (git
    # checkout) and the refactored one return bit-identical results
    # on these pinned inputs. (A scratch capture taken during recon
    # with unrecorded inputs -- p 0.532 -- could not be reproduced
    # and is superseded by this A/B pair; see docs/WORKLOG.md.)
    # Inputs refreshed 2026-11-04 at the corrections landing: the
    # pinned XIs were regenerated on the corrected squads/priors
    # (Iftikhar Ahmed removed, Ryan Burl integrated, Rashid Khan and
    # Sahil Patel registry ids corrected) and the distributions now
    # include Season 3 deliveries; expected values re-captured from
    # the deterministic seeded run (seed 3, verified reproducible).
    # Inputs refreshed 2026-11-11 at the Harry Tector integration:
    # Janakpur's pinned XI was regenerated (Tector in at index 2,
    # Anil Kumar Sah out of the prefix) and the expected values
    # re-captured from the deterministic seeded run (seed 3,
    # verified reproducible across two runs).
    assert res["p_team_1_win"] == pytest.approx(0.523)
    assert res["tie_rate"] == pytest.approx(0.018)
    assert res["mean_score_1"] == pytest.approx(140.798)
    assert res["mean_score_2"] == pytest.approx(135.22)
