"""Hand-computed tests for the single cricket metrics module
(src/cricket/metrics.py), per Section 4 of the upgraded master prompt.

Every expected value below was computed by hand from the worked examples
in docs/WORKLOG.md (2.1) before the module was written.
"""
import pandas as pd
import pytest

from src.cricket import metrics as cm

DATA = "data/normalized/ball_by_ball_normalized.parquet"
MATCHES = "data/normalized/matches_normalized.parquet"


# ---------- overs notation ----------
def test_overs_notation_never_float_arithmetic():
    assert cm.overs_to_balls("18.3") == 111
    assert cm.overs_to_balls("0.5") == 5
    assert cm.overs_to_balls("20.0") == 120
    assert cm.balls_to_overs(111) == "18.3"
    assert cm.balls_to_decimal_overs(111) == pytest.approx(18.5)
    with pytest.raises(ValueError):
        cm.overs_to_balls("18.6")  # 6 balls would be the next over


# ---------- phases (1-indexed overs: PP 1-6, middle 7-15, death 16-20)
def test_phase_boundaries():
    assert cm.phase_for_over(1) == "Powerplay"
    assert cm.phase_for_over(6) == "Powerplay"
    assert cm.phase_for_over(7) == "Middle"
    assert cm.phase_for_over(15) == "Middle"
    assert cm.phase_for_over(16) == "Death"
    assert cm.phase_for_over(20) == "Death"
    # the project data stores 0-indexed overs
    assert cm.phase_for_over_index0(0) == "Powerplay"
    assert cm.phase_for_over_index0(5) == "Powerplay"
    assert cm.phase_for_over_index0(6) == "Middle"
    assert cm.phase_for_over_index0(15) == "Death"


# ---------- the hand-worked 10-delivery innings ----------
def _delivery(off_bat, extras, xtype, dismissal=None):
    return {"runs_off_bat": off_bat, "runs_extras": extras,
            "extras_type": xtype, "is_wicket": dismissal is not None,
            "dismissal_type": dismissal}


INNINGS = [
    _delivery(4, 0, None),                    # A: four (legal)
    _delivery(0, 1, "wides"),                 # wide: not legal, not faced
    _delivery(1, 0, None),                    # A: single (legal)
    _delivery(2, 1, "noballs"),               # B: no-ball + 2 (faced, not legal)
    _delivery(0, 0, None, "bowled"),          # B: bowled (legal, credited)
    _delivery(0, 1, "legbyes"),               # C: leg-bye (legal, faced)
    _delivery(6, 0, None),                    # C: six (legal)
    _delivery(0, 2, "byes"),                  # C: 2 byes (legal, faced)
    _delivery(1, 0, None, "run out"),         # C: run out (legal, NOT credited)
    _delivery(0, 0, None),                    # D: dot (legal)
]


def test_ball_accounting():
    assert [cm.is_legal_ball(d["extras_type"]) for d in INNINGS] == [
        True, False, True, False, True, True, True, True, True, True]
    assert [cm.is_ball_faced(d["extras_type"]) for d in INNINGS] == [
        True, False, True, True, True, True, True, True, True, True]


def test_innings_attribution_hand_example():
    s = cm.innings_summary(INNINGS)
    assert s["batter_runs"] == 14
    assert s["extras_total"] == 5
    assert s["extras_breakdown"] == {"wides": 1, "noballs": 1,
                                     "legbyes": 1, "byes": 2}
    assert s["team_total"] == 19
    assert s["legal_balls"] == 8
    assert s["balls_faced"] == 9
    assert s["bowler_runs"] == 16        # byes + leg-byes excluded
    assert s["wickets_lost"] == 2
    assert s["bowler_wickets"] == 1      # run out not credited
    assert s["dot_balls"] == 2           # the bowled ball and the dot


def test_bowler_credited_wicket_set():
    for d in ["bowled", "caught", "caught and bowled", "lbw", "stumped",
              "hit wicket"]:
        assert cm.is_bowler_credited(d)
    for d in ["run out", "retired out", "retired hurt",
              "obstructing the field", "timed out", None]:
        assert not cm.is_bowler_credited(d)


# ---------- rates and undefined cases ----------
def test_rates_and_undefined_cases():
    assert cm.batting_strike_rate(5, 2) == pytest.approx(250.0)
    assert cm.batting_average(5, 0) is None        # never dismissed
    assert cm.batting_average(2, 1) == pytest.approx(2.0)
    assert cm.economy_rate(16, 8) == pytest.approx(12.0)
    assert cm.bowling_average(16, 1) == pytest.approx(16.0)
    assert cm.bowling_strike_rate(8, 1) == pytest.approx(8.0)
    assert cm.bowling_average(16, 0) is None       # no wickets
    assert cm.bowling_strike_rate(8, 0) is None
    assert cm.run_rate(19, 8) == pytest.approx(14.25)
    assert cm.required_run_rate(146, 100, 60) == pytest.approx(4.6)
    assert cm.required_run_rate(146, 146, 60) == pytest.approx(0.0)
    assert cm.required_run_rate(146, 100, 0) is None


# ---------- NRR: all-out rule + aggregation ----------
def test_nrr_all_out_counts_full_quota():
    # Team A all out for 100 in 12 overs; Team B 101/5 in 15 overs.
    recs = [
        {"batting_team": "A", "bowling_team": "B", "runs": 100,
         "legal_balls": 72, "wickets": 10},
        {"batting_team": "B", "bowling_team": "A", "runs": 101,
         "legal_balls": 90, "wickets": 5},
    ]
    nrr = cm.net_run_rate(recs)
    # A: scored 100/20ov = 5.0; conceded 101/15ov = 6.7333 -> -1.7333
    assert nrr["A"] == pytest.approx(5.0 - 101 / 15.0)
    assert nrr["B"] == pytest.approx(101 / 15.0 - 5.0)


def _season_innings(season, league_only=False):
    bb = pd.read_parquet(DATA)
    m = pd.read_parquet(MATCHES)
    sel = m.season == season
    if league_only:
        sel &= m.match_importance == "League"
    ids = set(m.loc[sel, "match_id"])
    bb = bb[bb.match_id.isin(ids)]
    recs = []
    for (_, inn), g in bb.groupby(["match_id", "innings"]):
        s = cm.innings_summary(g.to_dict("records"))
        recs.append({"batting_team": g.batting_team.iloc[0],
                     "bowling_team": g.bowling_team.iloc[0],
                     "runs": s["team_total"],
                     "legal_balls": s["legal_balls"],
                     "wickets": s["wickets_lost"]})
    return recs


def test_nrr_janakpur_s1_regression():
    """Audit regression case: with the all-out rule Janakpur's S1 NRR is
    +0.139; the approximation that ignores the rule gives +0.452."""
    nrr = cm.net_run_rate(_season_innings("S1"))
    assert nrr["Janakpur Bolts"] == pytest.approx(0.139, abs=0.002)
    assert abs(nrr["Janakpur Bolts"] - 0.452) > 0.1


def test_nrr_s2_secondary_crosscheck():
    """Secondary cross-check (NOT the C5 ground-truth test, which is
    BLOCKED on an official table — see docs/WORKLOG.md 2.4): the S2
    table published by cricnepal.com, whose For/Against columns are
    internally consistent, vs the module applied to project data."""
    published = {"Sudurpaschim Royals": 0.832, "Biratnagar Kings": 0.680,
                 "Kathmandu Gorkhas": 0.537, "Lumbini Lions": -0.394,
                 "Pokhara Avengers": -0.179, "Karnali Yaks": -0.356,
                 "Chitwan Rhinos": -0.611, "Janakpur Bolts": -0.443}
    # a league points table covers league matches only; the four
    # playoff teams' all-match NRRs differ exactly by their playoff
    # matches, which is how this scope was identified (see WORKLOG).
    nrr = cm.net_run_rate(_season_innings("S2", league_only=True))
    for team, expected in published.items():
        assert nrr[team] == pytest.approx(expected, abs=0.002), team
