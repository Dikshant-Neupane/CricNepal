"""Plan task 3.3 (criterion E3): the master-build squad validation
report encodes only the sourced Season 3 squad rule (6-8 overseas
per squad, docs/PLAYING_CONDITIONS.md). It flags, never fails.
Associate-presence is explicitly NOT CHECKED (status not sourced
in-repo); no total-squad-size limit is invented.
"""
from pathlib import Path

import pandas as pd

from src.prediction.squad_validation import validate_squads

ROOT = Path(__file__).resolve().parent.parent


def _master(spec):
    rows = []
    for team, (n, n_os) in spec.items():
        for i in range(n):
            rows.append(dict(player_key=f"{team}_{i}", team=team,
                             is_overseas=i < n_os))
    return pd.DataFrame(rows)


def test_flags_below_and_above_the_reported_range():
    rep = validate_squads(_master({"Low": (18, 5), "Ok": (19, 7),
                                   "High": (20, 9)})).set_index("team")
    assert not rep.loc["Low", "overseas_within_reported_range"]
    assert rep.loc["Ok", "overseas_within_reported_range"]
    assert not rep.loc["High", "overseas_within_reported_range"]
    assert rep.loc["Ok", "status"] == "ok"
    assert "FLAG" in rep.loc["Low", "status"]


def test_associate_clause_reported_not_checked():
    rep = validate_squads(_master({"T": (18, 6)}))
    assert rep.iloc[0]["associate_player_check"].startswith("NOT CHECKED")


def test_real_master_report_values():
    master = pd.read_csv(ROOT / "data/predictions/player_master.csv")
    rep = validate_squads(master).set_index("team")
    assert len(rep) == 8
    # branch snapshot (cut 2026-10-29): four squads sit at 5 overseas,
    # below the reported 6-8 registration range -- flagged for human
    # review, exactly what the report exists for.
    assert rep.loc["Janakpur Bolts", "n_overseas"] == 7
    assert rep.loc["Biratnagar Kings", "n_overseas"] == 5
    # 5 since 2026-11-05: K. S. Bharat's removal brought Kathmandu's
    # overseas squad count back inside the reported 6-8 range.
    # 6 since 2026-11-07: Grant Stewart's integration brought Lumbini's
    # overseas squad count (6) inside the reported 6-8 range.
    # 7 since 2026-11-08: Yuvraj Samra's integration brought Pokhara's
    # overseas squad count (6) inside the reported 6-8 range.
    assert int(rep["overseas_within_reported_range"].sum()) == 7
