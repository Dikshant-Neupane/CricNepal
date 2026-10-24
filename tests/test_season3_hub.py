"""Season 3 Hub: the page's data assembly must reflect the locked
artefacts exactly — 28 league fixtures with all four locked series,
the opener as next match, and standings that start empty."""
import pandas as pd

from src.dashboard.page_modules.season3_hub import compute_standings, load_season3

DATA = load_season3()


def test_hub_fixtures_complete_with_locks():
    fx = DATA["fixtures"]
    league = fx[fx.stage == "League"]
    assert len(league) == 28 and len(fx) == 32  # + Q1, Eliminator, Q2, Final
    for key in ["champion", "elo", "simulator", "coach"]:
        assert league[key].notna().all(), key


def test_hub_next_match_is_the_opener():
    nm = DATA["next_match"]
    assert nm["match_number"] == 1
    assert (nm["team_1"], nm["team_2"]) == ("Lumbini Lions", "Sudurpaschim Royals")
    assert str(nm["date"].date()) == "2026-10-26" and nm["time"] == "17:00"
    # Champion lock for the opener, from the frozen log (team_1 orientation)
    assert abs(nm["champion"] - 0.4799) < 1e-9


def test_hub_scorecard_locked_not_scored_preseason():
    for label, v in DATA["scorecard"].items():
        assert v["locked"] == 28, label
        assert v["scored"] == 0, label  # no S3 results ingested yet


def test_hub_standings_start_empty():
    teams = sorted(DATA["coaches"].team)
    st_ = compute_standings(DATA["fixtures"], teams)
    assert len(st_) == 8 and st_.P.sum() == 0 and st_.Pts.sum() == 0


def test_hub_squads_and_coaches_verified_counts():
    assert len(DATA["coaches"]) == 8
    assert DATA["coaches"].head_coach.notna().all()
    assert DATA["coaches"].captain.notna().all()
    assert len(DATA["squads"]) == 141
    jb = DATA["squads"][DATA["squads"].team == "Janakpur Bolts"]
    assert len(jb) == 17
