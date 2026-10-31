"""Plan task 2.3 (criterion C5): model.match_nrr must apply the
all-out full-quota rule (master prompt Section 4): an innings ending
all out counts as the full 20 overs, on both sides.

Hand example: A 100 all out (15.0 overs stored) v B 101/5 (19.0).
Correct A NRR = 100/20 - 101/19 = -0.3158. The pre-fix approximation
read 100/15 - 101/19 = +1.3509 -- it rewarded being bowled out.

Real-data conformance: on innings whose stored ball counts agree
with the canonical ball-by-ball (the CONF-003-consistent subset),
match_nrr must equal the per-match NRR derived independently from
deliveries via src/cricket/metrics. On the remaining innings the
stored summaries themselves are the registered CONF-003 conflict;
match_nrr's contract is the formula, not the stored data.
"""
from pathlib import Path

import pandas as pd
import pytest

from src.prediction import model as M
from src.cricket import metrics as CM

ROOT = Path(__file__).resolve().parent.parent


def _row(**kw):
    base = {"innings_1_team": "A", "innings_2_team": "B",
            "innings_1_runs": 100, "innings_1_overs": 15.0,
            "innings_1_wickets": 10,
            "innings_2_runs": 101, "innings_2_overs": 19.0,
            "innings_2_wickets": 5}
    base.update(kw)
    return base


def test_all_out_innings_counts_full_quota():
    assert M.match_nrr(_row(), "A") == pytest.approx(100 / 20 - 101 / 19)
    assert M.match_nrr(_row(), "B") == pytest.approx(101 / 19 - 100 / 20)


def test_not_all_out_uses_actual_overs():
    r = _row(innings_1_wickets=9)
    assert M.match_nrr(r, "A") == pytest.approx(100 / 15 - 101 / 19)


def test_missing_wickets_column_falls_back_to_actual_overs():
    r = _row()
    del r["innings_1_wickets"], r["innings_2_wickets"]
    assert M.match_nrr(r, "A") == pytest.approx(100 / 15 - 101 / 19)


def test_real_data_matches_delivery_derived_on_consistent_innings():
    m = pd.read_parquet(ROOT / "data/normalized/matches_normalized.parquet")
    bb = pd.read_parquet(ROOT / "data/normalized/ball_by_ball_normalized.parquet")
    bb = bb.copy()
    bb["legal"] = ~bb["extras_type"].isin(["wides", "noballs"])
    der = bb.groupby(["match_id", "innings"])["legal"].sum()
    checked = 0
    for _, row in m.iterrows():
        balls, ok = {}, True
        for inn in (1, 2):
            stored = M.overs_to_balls(row[f"innings_{inn}_overs"])
            try:
                d = float(der.loc[(row["match_id"], inn)])
            except KeyError:
                ok = False
                break
            if stored != d:
                ok = False
                break
            balls[inn] = int(d)
        if not ok:
            continue
        for team, mine, theirs in (
                (row["innings_1_team"], 1, 2), (row["innings_2_team"], 2, 1)):
            exp = (row[f"innings_{mine}_runs"]
                   / (CM.adjusted_balls(balls[mine], int(row[f"innings_{mine}_wickets"])) / 6)
                   - row[f"innings_{theirs}_runs"]
                   / (CM.adjusted_balls(balls[theirs], int(row[f"innings_{theirs}_wickets"])) / 6))
            got = M.match_nrr(row, team)
            assert got == pytest.approx(exp, abs=1e-9), (row["match_id"], team)
            checked += 1
    # 18 of 64 matches are fully consistent (36 team values); the
    # other 46 carry at least one CONF-003-discrepant innings and are
    # skipped by construction. Every checked value matched to 1e-9.
    assert checked >= 30
