"""TU par tables: internal consistency on the real 64-match dataset."""
import pandas as pd

from scripts.build_tu_par_tables import (chase_bands, load, par_summary,
                                         phase_par, wickets_by_type)

MATCHES, BBB = load()


def test_slot_derivation_rule():
    s1 = MATCHES[MATCHES.season == "S1"]
    assert (s1.slot == "Day").all()  # floodlights only arrived in S2
    assert int((MATCHES.slot == "Day-Night").sum()) == 9
    assert int((MATCHES.slot == "S2 single (slot unverified)").sum()) == 14


def test_par_summary_reconciles():
    row = par_summary(MATCHES).set_index("split").loc["All matches"]
    assert row.matches == 64
    # 63 decided + the S1 Super Over tie recorded as no winner
    assert row.bat_first_wins + row.chase_wins == 63
    assert row.inn1_mean == 147.5


def test_phase_runs_sum_to_innings_totals():
    pp = phase_par(BBB)
    allm = pp[pp.split == "All matches"]
    assert int(allm.runs.sum()) == int(
        MATCHES.innings_1_runs.sum() + MATCHES.innings_2_runs.sum())


def test_chase_bands_cover_all_decided_matches():
    cb = chase_bands(MATCHES)
    assert int(cb.matches.sum()) == 63
    assert int(cb.chase_wins.sum()) == 33


def test_wickets_by_type_spin_share_with_coverage():
    wt = wickets_by_type(BBB).set_index("season")
    for season in ["S1", "S2"]:
        assert wt.loc[season, "type_coverage_pct"] >= 95
        assert wt.loc[season, "spin_wkts"] > wt.loc[season, "pace_wkts"]
