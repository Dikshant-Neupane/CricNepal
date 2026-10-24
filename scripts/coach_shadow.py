"""Coach shadow probabilities for Season 3 (Pre-registration Amendment #7).

A SHADOW series, like the simulator: it never touches the frozen log,
never headlines, and is scored on the same 28 league fixtures at season
end. It exists to test, on pre-registered terms, whether head-coach
track record carries any predictive signal in this league.

Rule (frozen by Amendment #7, 2026-10-24, before Match 1):

    adj_elo(coach) = 25 * (win_pct - 0.50) * n / (n + 20),  capped at +/-15

where (n, win_pct) is the coach's COUNTABLE sample: T20 head-coach
matches whose win-loss record is sourced (see SAMPLES; full sourcing in
the coach dossiers). Coaches without a countable sample get adj = 0,
recorded as "no measurement" -- NOT as "average coach".

    p_elo_adj  = Elo expectation with (diff + adj_1 - adj_2)
    p_shadow   = clip(0.5 * p_elo_adj + 0.5 * p_xi)   [champion's form]

with p_xi recovered from the locked champion row (p = .5 p_elo + .5 p_xi).

Run:  python scripts/coach_shadow.py
Out:  data/predictions/coach_shadow.csv (28 rows; frozen_log untouched)
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent
PRED = ROOT / "data" / "predictions"

# Countable head-coach T20 samples (wins, losses) -- sourced, see
# files/s3-auction-squads/coach_dossiers.md (goal workspace) and the
# notes in Amendment #7. Excluded by rule: unofficial aggregates
# (Desai's Nepal totals), assistant/specialist stints, partial-tenure
# numbers (Misbah's interim PCB T20I split is a partial sample of a
# larger tenure and is excluded for consistency -- see amendment).
SAMPLES = {
    # team: (coach, wins, losses, sample_note)
    "Lumbini Lions": ("Tinu Yohannan", 7, 3,
                      "NPL S2 title run, fully scorecard-sourced"),
    "Kathmandu Gorkhas": ("Monty Desai", 5, 3,
                          "NPL S2 (league 5-2 + playoff loss), from match data"),
    "Karnali Yaks": ("Gyanendra Malla", 7, 9,
                     "NPL S1+S2, countable from match data"),
    "Janakpur Bolts": ("Shivnarine Chanderpaul", 12, 16,
                       "CPL 2022 (league 4-5 + 3-0 playoffs) + CPL 2023 league 4-5 "
                       "+ NPL S2 1-6; no-result matches excluded"),
    "Sudurpaschim Royals": ("Misbah-ul-Haq", 0, 0,
                            "No countable sample by rule (see Amendment #7)"),
    "Biratnagar Kings": ("Dhammika Prasad", 0, 0,
                         "No head-coach sample (specialist/assistant roles only)"),
    "Chitwan Rhinos": ("Sohail Tanvir", 0, 0,
                       "First head-coach appointment (0 matches)"),
    "Pokhara Avengers": ("Ajantha Mendis", 0, 0,
                         "First head-coach appointment (0 matches)"),
}

SHRINK_K = 20.0
SCALE = 25.0
CAP = 15.0
CLIP = (0.05, 0.95)


def coach_adjustment(wins: int, losses: int) -> float:
    n = wins + losses
    if n == 0:
        return 0.0
    win_pct = wins / n
    adj = SCALE * (win_pct - 0.50) * n / (n + SHRINK_K)
    return float(max(-CAP, min(CAP, adj)))


def adjustments() -> dict[str, float]:
    return {team: coach_adjustment(w, l) for team, (_, w, l, _) in SAMPLES.items()}


def elo_expected_from_diff(diff: float) -> float:
    return 1.0 / (1.0 + 10.0 ** (-diff / 400.0))


def diff_from_prob(p: float) -> float:
    return 400.0 * math.log10(p / (1.0 - p))


def main() -> None:
    frozen = pd.read_csv(PRED / "frozen_log.csv")
    p1 = frozen[frozen.stage == "P1_preseason_expected_xi"].copy()
    adj = adjustments()
    now = datetime.now(timezone.utc).isoformat()
    rows = []
    for r in p1.itertuples():
        p_xi = 2.0 * r.p_team_1_win - r.p_elo
        diff = diff_from_prob(r.p_elo)
        diff_adj = diff + adj.get(r.team_1_name, 0.0) - adj.get(r.team_2_name, 0.0)
        p_elo_adj = elo_expected_from_diff(diff_adj)
        p_shadow = min(CLIP[1], max(CLIP[0], 0.5 * p_elo_adj + 0.5 * p_xi))
        rows.append({
            "match_id": r.match_id, "season": "S3",
            "stage": "COACH_shadow_preseason", "timestamp_locked": now,
            "model_version": "coach-shadow-v1",
            "team_1_name": r.team_1_name, "team_2_name": r.team_2_name,
            "p_team_1_win": round(p_shadow, 4),
            "p_champion": r.p_team_1_win, "p_elo": r.p_elo,
            "features_json": json.dumps({
                "adj_elo_team_1": round(adj.get(r.team_1_name, 0.0), 2),
                "adj_elo_team_2": round(adj.get(r.team_2_name, 0.0), 2),
                "coach_team_1": SAMPLES[r.team_1_name][0],
                "coach_team_2": SAMPLES[r.team_2_name][0],
            }),
        })
    out = pd.DataFrame(rows)
    out.to_csv(PRED / "coach_shadow.csv", index=False)
    print(f"wrote {len(out)} rows to data/predictions/coach_shadow.csv")
    print("adjustments:", {t: round(a, 2) for t, a in adj.items()})


if __name__ == "__main__":
    main()
