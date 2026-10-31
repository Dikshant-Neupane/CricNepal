"""Squad-rule validation report (plan task 3.3, criterion E3).

Encodes ONLY what docs/PLAYING_CONDITIONS.md actually supports for
Season 3 squads: each franchise may register 6 to 8 overseas players
(REPORTED-CORROBORATED). The same source states at least one squad
player must come from an ICC Associate Member nation, but Associate
status per player is not data this repository holds (nationality is
recorded; ICC membership status of each nationality is not sourced
in-repo), so that clause is reported as NOT CHECKED rather than
guessed. No sourced total-squad-size limit exists in the doc; squad
size is reported as information only.

This is a REPORT, not a gate: squads evolve during the season
(signings land between builds), so an out-of-range count is a flag
for human review at master-build time, never a build failure.
"""
from __future__ import annotations

import pandas as pd

OVERSEAS_MIN = 6
OVERSEAS_MAX = 8
ASSOCIATE_CHECK = ("NOT CHECKED - Associate-nation status per player "
                   "is not sourced in this repository")


def validate_squads(master: pd.DataFrame) -> pd.DataFrame:
    """One row per team in a player_master frame."""
    rows = []
    for team, g in sorted(master.groupby("team")):
        n_os = int(g["is_overseas"].astype(bool).sum())
        within = OVERSEAS_MIN <= n_os <= OVERSEAS_MAX
        rows.append({
            "team": team,
            "squad_size": int(len(g)),
            "n_overseas": n_os,
            "overseas_rule": f"{OVERSEAS_MIN}-{OVERSEAS_MAX} per squad "
                             f"(docs/PLAYING_CONDITIONS.md, "
                             f"REPORTED-CORROBORATED)",
            "overseas_within_reported_range": within,
            "associate_player_check": ASSOCIATE_CHECK,
            "status": "ok" if within else "FLAG: outside reported range "
                                          "- human review (squads evolve "
                                          "in-season; not a build failure)",
        })
    return pd.DataFrame(rows)
