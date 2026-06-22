"""
Opposition-Strength Controls (Elo + Strength of Schedule)
=========================================================

Builds a per-team Elo rating from the chronological match log and uses it to
quantify the opposition strength faced by Janakpur Bolts in each season.

Why this exists
---------------
The S1 → S2 win-rate decline (70% → 14%) is statistically significant on its
own, but with n=10 / n=7 it is plausible that schedule strength changed too.
Without an opposition control, "JAB got worse" cannot be cleanly distinguished
from "JAB faced harder opposition." This module computes:

1. **Elo rating per team** updated after every match (chronological order).
2. **Strength of schedule (SOS)** for JAB each season = mean pre-match Elo of
   each opponent JAB faced.
3. **Expected win probability** for each JAB match using the standard Elo
   formula `E = 1 / (1 + 10^((opp - team) / 400))`.
4. **Elo-adjusted win rate**: actual wins minus expected wins ("Wins Above
   Expected"). Positive = JAB outperformed schedule, negative = underperformed.
5. **Bootstrap confidence interval** on WAE per season to give a feel for how
   noisy the estimate is at this sample size.

Modelling notes
---------------
- Initial rating: 1500 for every team. Ties are scored as 0.5 / 0.5 (only one
  match in the dataset is a tie).
- K-factor: 24. Slightly higher than chess's 20 to allow faster adaptation in
  a short league. Sensitivity to K is reported.
- **Inter-season regression**: at the start of S2 each team's end-of-S1 rating
  is shrunk halfway back to 1500 (`r_s2_start = 0.5 * r_s1_end + 0.5 * 1500`).
  This is standard practice for sports Elo across season breaks; rosters
  change. Sensitivity to the shrinkage factor is reported.
- No home-court adjustment because every match is at a single venue (Kirtipur).
- Margin-of-victory adjustment is intentionally omitted to keep the model
  simple and interpretable; the goal here is opposition control, not ranking.

Outputs
-------
- `data/exports/team_elo_history.csv`: pre- and post-match Elo for every match.
- `data/exports/janakpur_opposition_strength.csv`: per-match SOS + expected win
  probability + actual outcome.
- `data/exports/opposition_strength_analysis.png`: visual summary.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.utils.logging_config import get_logger

logger = get_logger(__name__)

try:
    from src.config.paths import EXPORT_DIR, NORMALIZED_DIR
except ImportError:  # pragma: no cover
    NORMALIZED_DIR = Path(__file__).resolve().parent.parent / "data" / "normalized"
    EXPORT_DIR = Path(__file__).resolve().parent.parent / "data" / "exports"

EXPORT_DIR.mkdir(parents=True, exist_ok=True)

TEAM = "Janakpur Bolts"
INITIAL_ELO = 1500.0
DEFAULT_K = 24.0
DEFAULT_SEASON_SHRINKAGE = 0.5  # 0 = no carry-over; 1 = full carry-over


@dataclass
class EloRow:
    match_id: str
    season: str
    match_date: pd.Timestamp
    team_1: str
    team_2: str
    team_1_pre: float
    team_2_pre: float
    team_1_post: float
    team_2_post: float
    winner: str | None
    score_team_1: float  # 1.0 win, 0.5 tie, 0.0 loss


def _expected(rating_a: float, rating_b: float) -> float:
    """Standard Elo expected score for player A vs B."""
    return 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))


def _outcome_score(row: pd.Series, team: str) -> float | None:
    """Return 1, 0.5, 0, or None (no result) for `team` in `row`."""
    if row["result_status"] == "tie":
        return 0.5
    winner = row["winner_name"]
    if pd.isna(winner):
        return None
    if winner == team:
        return 1.0
    return 0.0


def compute_elo_history(
    matches: pd.DataFrame,
    k: float = DEFAULT_K,
    season_shrinkage: float = DEFAULT_SEASON_SHRINKAGE,
) -> pd.DataFrame:
    """Return one row per match with pre- and post-match Elo for both teams.

    Matches are processed in chronological order. Teams unseen so far start
    at INITIAL_ELO. At a season boundary, ratings are partially regressed
    toward INITIAL_ELO (shrinkage controlled by `season_shrinkage`):

        r_new_season = season_shrinkage * (INITIAL_ELO) + (1 - season_shrinkage) * r_old

    so ``season_shrinkage = 0`` means full carry-over and
    ``season_shrinkage = 1`` means a full reset.
    """
    matches_sorted = matches.copy()
    matches_sorted["match_date"] = pd.to_datetime(matches_sorted["match_date"])
    matches_sorted = matches_sorted.sort_values(["season", "match_date", "match_id"])

    ratings: Dict[str, float] = {}
    last_season: str | None = None
    history: List[EloRow] = []

    for _, row in matches_sorted.iterrows():
        season = row["season"]
        if last_season is not None and season != last_season:
            # Season boundary: shrink every active team's rating back toward
            # the prior mean.
            for t in list(ratings.keys()):
                ratings[t] = (
                    season_shrinkage * INITIAL_ELO
                    + (1.0 - season_shrinkage) * ratings[t]
                )
        last_season = season

        t1, t2 = row["team_1_name"], row["team_2_name"]
        r1 = ratings.get(t1, INITIAL_ELO)
        r2 = ratings.get(t2, INITIAL_ELO)

        s1 = _outcome_score(row, t1)
        s2 = _outcome_score(row, t2)

        if s1 is None or s2 is None:
            # No result; record but do not update ratings.
            history.append(
                EloRow(
                    match_id=row["match_id"],
                    season=season,
                    match_date=row["match_date"],
                    team_1=t1,
                    team_2=t2,
                    team_1_pre=r1,
                    team_2_pre=r2,
                    team_1_post=r1,
                    team_2_post=r2,
                    winner=row.get("winner_name"),
                    score_team_1=np.nan,
                )
            )
            ratings[t1], ratings[t2] = r1, r2
            continue

        e1 = _expected(r1, r2)
        e2 = 1.0 - e1

        r1_new = r1 + k * (s1 - e1)
        r2_new = r2 + k * (s2 - e2)

        ratings[t1], ratings[t2] = r1_new, r2_new

        history.append(
            EloRow(
                match_id=row["match_id"],
                season=season,
                match_date=row["match_date"],
                team_1=t1,
                team_2=t2,
                team_1_pre=r1,
                team_2_pre=r2,
                team_1_post=r1_new,
                team_2_post=r2_new,
                winner=row.get("winner_name"),
                score_team_1=s1,
            )
        )

    return pd.DataFrame([row.__dict__ for row in history])


def opposition_strength_for_team(
    elo_history: pd.DataFrame, team: str = TEAM
) -> pd.DataFrame:
    """Build a per-match opposition-strength table for `team`.

    For each match `team` played in, returns:
      - opponent name
      - opponent pre-match Elo (= strength of opposition for that match)
      - team pre-match Elo
      - expected win probability
      - actual outcome (1 / 0.5 / 0)
    """
    rows: List[Dict] = []
    for _, m in elo_history.iterrows():
        if m["team_1"] == team:
            opp = m["team_2"]
            opp_pre = m["team_2_pre"]
            team_pre = m["team_1_pre"]
            actual = m["score_team_1"]
        elif m["team_2"] == team:
            opp = m["team_1"]
            opp_pre = m["team_1_pre"]
            team_pre = m["team_2_pre"]
            actual = (
                np.nan if pd.isna(m["score_team_1"]) else (1.0 - m["score_team_1"])
            )
        else:
            continue

        expected = _expected(team_pre, opp_pre)
        rows.append(
            {
                "match_id": m["match_id"],
                "season": m["season"],
                "match_date": m["match_date"],
                "opponent": opp,
                "team_pre_elo": round(team_pre, 1),
                "opp_pre_elo": round(opp_pre, 1),
                "expected_win_pct": round(expected * 100, 1),
                "actual_score": actual,  # 1 / 0.5 / 0 / NaN
                "wins_above_expected": (actual - expected) if pd.notna(actual) else np.nan,
            }
        )
    return pd.DataFrame(rows)


def season_summary(opp_strength: pd.DataFrame) -> pd.DataFrame:
    """Aggregate per-match opposition-strength rows into a per-season view."""
    out: List[Dict] = []
    for season in sorted(opp_strength["season"].unique()):
        s = opp_strength[opp_strength["season"] == season]
        played = s.dropna(subset=["actual_score"])
        wins = float(played["actual_score"].sum())
        n = len(played)
        win_pct = wins / n * 100 if n else 0.0
        sos = s["opp_pre_elo"].mean()
        expected_wins = s["expected_win_pct"].sum() / 100
        wae = wins - expected_wins
        out.append(
            {
                "season": season,
                "matches": n,
                "wins": wins,
                "win_pct": round(win_pct, 1),
                "sos_mean_opp_elo": round(sos, 1),
                "expected_wins": round(expected_wins, 2),
                "expected_win_pct": round(expected_wins / n * 100, 1) if n else 0.0,
                "wins_above_expected": round(wae, 2),
                "wae_per_match": round(wae / n, 3) if n else 0.0,
            }
        )
    return pd.DataFrame(out)


def bootstrap_wae(
    opp_strength: pd.DataFrame, n_iter: int = 2000, seed: int = 17
) -> pd.DataFrame:
    """95% bootstrap CI on Wins Above Expected, per season.

    For each season, resample matches with replacement and recompute WAE.
    """
    rng = np.random.default_rng(seed)
    rows: List[Dict] = []
    for season in sorted(opp_strength["season"].unique()):
        s = opp_strength[opp_strength["season"] == season].dropna(
            subset=["actual_score"]
        )
        n = len(s)
        if n == 0:
            continue
        actual = s["actual_score"].to_numpy()
        expected = s["expected_win_pct"].to_numpy() / 100.0
        wae_obs = float(np.sum(actual - expected))
        boot = np.empty(n_iter, dtype=float)
        for i in range(n_iter):
            idx = rng.integers(0, n, size=n)
            boot[i] = float(np.sum(actual[idx] - expected[idx]))
        lo, hi = np.percentile(boot, [2.5, 97.5])
        rows.append(
            {
                "season": season,
                "n": n,
                "wae_observed": round(wae_obs, 2),
                "wae_ci_lo": round(float(lo), 2),
                "wae_ci_hi": round(float(hi), 2),
                "wae_per_match_observed": round(wae_obs / n, 3),
                "wae_per_match_ci_lo": round(float(lo) / n, 3),
                "wae_per_match_ci_hi": round(float(hi) / n, 3),
            }
        )
    return pd.DataFrame(rows)


def k_sensitivity(
    matches: pd.DataFrame, k_values: Tuple[float, ...] = (16.0, 24.0, 32.0)
) -> pd.DataFrame:
    """How much does the per-season WAE depend on the K-factor choice?"""
    rows: List[Dict] = []
    for k in k_values:
        elo = compute_elo_history(matches, k=k)
        opp = opposition_strength_for_team(elo, TEAM)
        for season, df in opp.groupby("season"):
            played = df.dropna(subset=["actual_score"])
            wins = float(played["actual_score"].sum())
            n = len(played)
            sos = df["opp_pre_elo"].mean()
            expected = df["expected_win_pct"].sum() / 100
            rows.append(
                {
                    "k": k,
                    "season": season,
                    "n": n,
                    "wins": wins,
                    "sos_mean_opp_elo": round(sos, 1),
                    "expected_wins": round(expected, 2),
                    "wae": round(wins - expected, 2),
                }
            )
    return pd.DataFrame(rows)


def shrinkage_sensitivity(
    matches: pd.DataFrame,
    shrinkages: Tuple[float, ...] = (0.0, 0.25, 0.5, 0.75, 1.0),
) -> pd.DataFrame:
    """How much does the inter-season shrinkage assumption matter?"""
    rows: List[Dict] = []
    for s in shrinkages:
        elo = compute_elo_history(matches, season_shrinkage=s)
        opp = opposition_strength_for_team(elo, TEAM)
        for season, df in opp.groupby("season"):
            played = df.dropna(subset=["actual_score"])
            wins = float(played["actual_score"].sum())
            n = len(played)
            sos = df["opp_pre_elo"].mean()
            expected = df["expected_win_pct"].sum() / 100
            rows.append(
                {
                    "season_shrinkage": s,
                    "season": season,
                    "n": n,
                    "wins": wins,
                    "sos_mean_opp_elo": round(sos, 1),
                    "expected_wins": round(expected, 2),
                    "wae": round(wins - expected, 2),
                }
            )
    return pd.DataFrame(rows)


def create_visualizations(
    elo_history: pd.DataFrame,
    opp_strength: pd.DataFrame,
    summary: pd.DataFrame,
) -> Path:
    """Three-panel visual: Elo trajectories, JAB SOS per match, season summary."""
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    # --- Panel 1: Elo trajectories for all teams ---
    ax = axes[0]
    teams = sorted(set(elo_history["team_1"]).union(set(elo_history["team_2"])))
    for t in teams:
        # Build a chronological series of post-match Elo for this team
        series = []
        for _, m in elo_history.iterrows():
            if m["team_1"] == t:
                series.append((m["match_date"], m["team_1_post"]))
            elif m["team_2"] == t:
                series.append((m["match_date"], m["team_2_post"]))
        if not series:
            continue
        s = pd.DataFrame(series, columns=["date", "elo"]).sort_values("date")
        line, = ax.plot(s["date"], s["elo"], marker="o", markersize=3, linewidth=1.2, label=t,
                         alpha=0.95 if t == TEAM else 0.55)
        if t == TEAM:
            line.set_linewidth(2.4)
    ax.axhline(INITIAL_ELO, color="grey", linestyle="--", linewidth=0.8)
    ax.set_title("Elo trajectories")
    ax.set_xlabel("Match date")
    ax.set_ylabel("Elo (post-match)")
    ax.legend(loc="best", fontsize=7, ncol=2)
    for label in ax.get_xticklabels():
        label.set_rotation(30)
        label.set_horizontalalignment("right")

    # --- Panel 2: JAB strength of schedule per match ---
    ax = axes[1]
    for season, color in zip(["S1", "S2"], ["#4CAF50", "#F44336"]):
        s = opp_strength[opp_strength["season"] == season].sort_values("match_date")
        ax.plot(
            s["match_date"],
            s["opp_pre_elo"],
            marker="o",
            label=f"{season} opp Elo",
            color=color,
            linewidth=2,
        )
    ax.axhline(INITIAL_ELO, color="grey", linestyle="--", linewidth=0.8)
    ax.set_title("Janakpur Bolts: opponent Elo per match")
    ax.set_xlabel("Match date")
    ax.set_ylabel("Opponent pre-match Elo")
    ax.legend()
    for label in ax.get_xticklabels():
        label.set_rotation(30)
        label.set_horizontalalignment("right")

    # --- Panel 3: WAE bar with 95% bootstrap CI ---
    ax = axes[2]
    if not summary.empty:
        seasons = summary["season"].tolist()
        wae = summary["wins_above_expected"].tolist()
        colors = ["#4CAF50" if v >= 0 else "#F44336" for v in wae]
        ax.bar(seasons, wae, color=colors, edgecolor="black", alpha=0.85)
        for i, (s, v) in enumerate(zip(seasons, wae)):
            ax.text(i, v + (0.05 if v >= 0 else -0.15), f"{v:+.2f}",
                    ha="center", fontweight="bold")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_title("Wins above expected (Elo-adjusted)")
    ax.set_xlabel("Season")
    ax.set_ylabel("Actual wins − expected wins")

    plt.tight_layout()
    out = EXPORT_DIR / "opposition_strength_analysis.png"
    plt.savefig(out, dpi=150)
    plt.close()
    logger.info("Saved: %s", out)
    return out


def main() -> Dict:
    logger.info("=" * 80)
    logger.info("OPPOSITION-STRENGTH ANALYSIS (Elo + SOS)")
    logger.info("=" * 80)

    matches = pd.read_parquet(NORMALIZED_DIR / "matches_normalized.parquet")
    elo = compute_elo_history(matches)
    opp = opposition_strength_for_team(elo, TEAM)
    summary = season_summary(opp)
    boot = bootstrap_wae(opp)
    k_sens = k_sensitivity(matches)
    shrink_sens = shrinkage_sensitivity(matches)

    logger.info("\nPer-match opposition strength (head):\n%s",
                opp.head(8).to_string(index=False))

    logger.info("\nPer-season summary:\n%s", summary.to_string(index=False))
    logger.info("\nBootstrap 95%% CI on WAE:\n%s", boot.to_string(index=False))
    logger.info("\nK-factor sensitivity:\n%s", k_sens.to_string(index=False))
    logger.info("\nInter-season shrinkage sensitivity:\n%s",
                shrink_sens.to_string(index=False))

    # Persist tables
    elo_out = EXPORT_DIR / "team_elo_history.csv"
    opp_out = EXPORT_DIR / "janakpur_opposition_strength.csv"
    summary_out = EXPORT_DIR / "janakpur_season_strength_summary.csv"
    boot_out = EXPORT_DIR / "janakpur_wae_bootstrap.csv"
    k_out = EXPORT_DIR / "elo_k_sensitivity.csv"
    shrink_out = EXPORT_DIR / "elo_shrinkage_sensitivity.csv"
    elo.to_csv(elo_out, index=False)
    opp.to_csv(opp_out, index=False)
    summary.to_csv(summary_out, index=False)
    boot.to_csv(boot_out, index=False)
    k_sens.to_csv(k_out, index=False)
    shrink_sens.to_csv(shrink_out, index=False)
    logger.info("Saved: %s, %s, %s, %s, %s, %s",
                elo_out, opp_out, summary_out, boot_out, k_out, shrink_out)

    create_visualizations(elo, opp, summary)

    return {
        "elo_history": elo,
        "opposition_strength": opp,
        "season_summary": summary,
        "bootstrap": boot,
        "k_sensitivity": k_sens,
        "shrinkage_sensitivity": shrink_sens,
    }


if __name__ == "__main__":
    main()
