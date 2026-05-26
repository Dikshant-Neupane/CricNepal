"""
Multi-Criteria Shortlist Matrix — Janakpur Bolts S3 Recruiting
==============================================================
Priority #5: Replace single-metric ranking with a transparent weighted scorecard.

Criteria and weights:
  sos_economy          0.30   (lower = better)
  dot_ball_pct         0.20   (higher = better)
  death_economy        0.20   (lower = better)
  balls_bowled         0.10   (more = higher confidence)
  econ_trend_s1_s2     0.10   (negative = improving)
  age_factor           0.05   (prime age 24-30 scores highest)
  bowling_type_fit     0.05   (pace in NPL conditions = slight bonus)

Each criterion normalised 0–10 before weighting.
Final shortlist score = weighted sum (max 10).

Output:
  deliverables/janakpur_s3_shortlist_matrix.csv   (all bowlers)
  deliverables/janakpur_s3_shortlist_top15.md     (top-15 markdown)

Usage:
  python scripts/shortlist_matrix.py
"""

import os
import numpy as np
import pandas as pd

ROOT      = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR  = os.path.join(ROOT, "data")
DELIV     = os.path.join(ROOT, "deliverables")
os.makedirs(DELIV, exist_ok=True)

# ─── Weights ──────────────────────────────────────────────────────────────────
WEIGHTS = {
    "sos_economy":      0.30,
    "dot_ball_pct":     0.20,
    "death_economy":    0.20,
    "balls_bowled":     0.10,
    "econ_trend_s1_s2": 0.10,
    "age_factor":       0.05,
    "bowling_type_fit": 0.05,
}
assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9, "Weights must sum to 1.0"

ENRICH_PATH = r"D:/cric_data/data/player_profiles/enriched_players_20260521.csv"


# ─── Normalisation helpers ────────────────────────────────────────────────────
def norm_minmax_lower_better(series: pd.Series, clip_pct: float = 0.05) -> pd.Series:
    """Lower raw value → higher 0–10 score."""
    lo = series.quantile(clip_pct)
    hi = series.quantile(1 - clip_pct)
    clipped = series.clip(lo, hi)
    norm = 1.0 - (clipped - lo) / (hi - lo + 1e-9)
    return norm * 10


def norm_minmax_higher_better(series: pd.Series, clip_pct: float = 0.05) -> pd.Series:
    """Higher raw value → higher 0–10 score."""
    lo = series.quantile(clip_pct)
    hi = series.quantile(1 - clip_pct)
    clipped = series.clip(lo, hi)
    norm = (clipped - lo) / (hi - lo + 1e-9)
    return norm * 10


def age_score(age: float) -> float:
    """
    Age factor score (0–10).
    Prime bowling age for T20 is roughly 24–30.
    Under 24 → development upside, slight discount.
    Over 33 → decline risk, progressive discount.
    """
    if pd.isna(age):
        return 5.0  # neutral if unknown
    if 24 <= age <= 30:
        return 10.0
    elif age < 24:
        # ramp up from 0 at 18 to 10 at 24
        return max(0.0, (age - 18) / (24 - 18) * 10)
    elif 30 < age <= 33:
        return 8.0 - (age - 30) * 1.5
    else:
        return max(0.0, 5.0 - (age - 33) * 1.5)


def bowling_type_fit(btype: str) -> float:
    """
    NPL pitch fit score (0–10).
    Pace (fast/medium-fast) tends to perform well in Kathmandu altitude.
    Spin is effective in later overs but less dominant.
    """
    if pd.isna(btype):
        return 5.0
    bt = str(btype).strip().lower()
    if "pace" in bt and "medium" not in bt:
        return 9.0
    elif "medium" in bt and "pace" in bt:
        return 8.0
    elif "medium" in bt:
        return 7.0
    elif "spin" in bt:
        return 6.5
    else:
        return 5.0


# ─── Data loading ────────────────────────────────────────────────────────────
def load_phase_data() -> pd.DataFrame:
    path = os.path.join(DATA_DIR, "per_bowler_season_features.csv")
    df = pd.read_csv(path)
    df["season_norm"] = df["season"].apply(_norm_season)
    df = df.rename(columns={"bowler": "player_name"})
    # compute total economy per season
    df["total_balls"] = df["powerplay_balls"].fillna(0) + df["death_balls"].fillna(0)
    pp_runs  = df["powerplay_econ"].fillna(0) * df["powerplay_balls"].fillna(0) / 6
    dth_runs = df["death_econ"].fillna(0) * df["death_balls"].fillna(0) / 6
    df["economy"] = np.where(
        df["total_balls"] > 0,
        (pp_runs + dth_runs) / (df["total_balls"] / 6),
        np.nan,
    )
    return df


def _norm_season(x) -> int:
    s = str(x).strip().upper()
    if s.startswith("S") and len(s) <= 3:
        return int(s.replace("S", ""))
    if "SEASON" in s:
        return int(s.split()[-1])
    try:
        return int(s)
    except Exception:
        return -1


def load_sos_adjusted() -> pd.DataFrame:
    """Try loading the SOS-adjusted shortlist produced by earlier scripts."""
    sos_path = os.path.join(DELIV, "s3_bowler_shortlist_sos.csv")
    if os.path.exists(sos_path):
        df = pd.read_csv(sos_path)
        if "sos_adj_economy" not in df.columns and "sos_adjusted_economy" in df.columns:
            df = df.rename(columns={"sos_adjusted_economy": "sos_adj_economy"})
        return df
    return pd.DataFrame()


# ─── Main build logic ────────────────────────────────────────────────────────
def build_matrix() -> pd.DataFrame:
    phase_df = load_phase_data()

    # Separate S1 and S2 rows
    s1 = phase_df[phase_df["season_norm"] == 1].set_index("player_name")
    s2 = phase_df[phase_df["season_norm"] == 2].set_index("player_name")

    # All players seen in S2 (minimum 12 balls)
    s2 = s2[s2["total_balls"] >= 12].copy()

    # Economy trend: s2 - s1 (negative = improving)
    common = sorted(set(s1.index) & set(s2.index))
    trend = {p: s2.loc[p, "economy"] - s1.loc[p, "economy"] for p in common if
             not pd.isna(s2.loc[p, "economy"]) and not pd.isna(s1.loc[p, "economy"])}

    s2["econ_trend_s1_s2"] = s2.index.map(trend)

    # SOS-adjusted economy
    sos_df = load_sos_adjusted()
    if not sos_df.empty and "sos_adj_economy" in sos_df.columns:
        sos_map = sos_df.set_index(
            sos_df.columns[sos_df.columns.str.contains("player|bowler", case=False)][0]
        )["sos_adj_economy"].to_dict()
    else:
        sos_map = {}

    s2["sos_economy"] = s2.index.map(sos_map)
    # fallback: use raw economy if no SOS-adjusted value
    s2["sos_economy"] = s2["sos_economy"].combine_first(s2["economy"])

    # Merge age + bowling type
    if os.path.exists(ENRICH_PATH):
        enrich = pd.read_csv(ENRICH_PATH)[["player_name", "bowling_type", "age"]].dropna(subset=["player_name"])
        enrich = enrich.set_index("player_name")
        s2["bowling_type"] = s2.index.map(enrich["bowling_type"])
        s2["age"]          = s2.index.map(enrich["age"])
    else:
        s2["bowling_type"] = np.nan
        s2["age"]          = np.nan

    s2 = s2.reset_index()

    # ── Pre-compute raw criteria columns ──
    s2["age_factor_raw"]       = s2["age"].apply(age_score)
    s2["bowling_type_fit_raw"] = s2["bowling_type"].apply(bowling_type_fit)
    s2["balls_bowled"]         = s2["total_balls"]
    s2["dot_ball_pct"]         = (
        (s2["powerplay_dot_pct"].fillna(0) * s2["powerplay_balls"].fillna(0) +
         s2["death_dot_pct"].fillna(0) * s2["death_balls"].fillna(0)) /
        s2["total_balls"].replace(0, np.nan) * 100
    )

    # Fill missing death econ with overall econ (worst-case fallback)
    s2["death_econ_raw"] = s2["death_econ"].combine_first(s2["economy"])

    # ── Normalise each criterion ──
    # Lower econ = better → invert
    s2["score_sos_economy"]      = norm_minmax_lower_better(s2["sos_economy"])
    s2["score_dot_ball_pct"]     = norm_minmax_higher_better(s2["dot_ball_pct"].fillna(0))
    s2["score_death_economy"]    = norm_minmax_lower_better(s2["death_econ_raw"])
    s2["score_balls_bowled"]     = norm_minmax_higher_better(s2["balls_bowled"])
    # Negative trend = improvement = better → invert
    s2["score_econ_trend_s1_s2"] = norm_minmax_lower_better(
        s2["econ_trend_s1_s2"].fillna(0)
    )
    # These are already 0–10
    s2["score_age_factor"]       = s2["age_factor_raw"]
    s2["score_bowling_type_fit"] = s2["bowling_type_fit_raw"]

    # ── Weighted total ──
    s2["shortlist_score"] = (
        WEIGHTS["sos_economy"]      * s2["score_sos_economy"] +
        WEIGHTS["dot_ball_pct"]     * s2["score_dot_ball_pct"] +
        WEIGHTS["death_economy"]    * s2["score_death_economy"] +
        WEIGHTS["balls_bowled"]     * s2["score_balls_bowled"] +
        WEIGHTS["econ_trend_s1_s2"] * s2["score_econ_trend_s1_s2"] +
        WEIGHTS["age_factor"]       * s2["score_age_factor"] +
        WEIGHTS["bowling_type_fit"] * s2["score_bowling_type_fit"]
    )

    # ── Tier labels ──
    q75 = s2["shortlist_score"].quantile(0.75)
    q50 = s2["shortlist_score"].quantile(0.50)

    def score_tier(sc):
        if sc >= q75:
            return "TIER-1 PRIORITY"
        elif sc >= q50:
            return "TIER-2 CONSIDER"
        else:
            return "TIER-3 MONITOR"

    s2["shortlist_tier"] = s2["shortlist_score"].apply(score_tier)
    s2 = s2.sort_values("shortlist_score", ascending=False).reset_index(drop=True)
    s2["rank"] = s2.index + 1

    return s2


# ─── Output writers ──────────────────────────────────────────────────────────
def write_csv(df: pd.DataFrame):
    cols = [
        "rank", "player_name", "shortlist_score", "shortlist_tier",
        "sos_economy", "dot_ball_pct", "death_econ_raw", "balls_bowled",
        "econ_trend_s1_s2", "age", "bowling_type",
        "score_sos_economy", "score_dot_ball_pct", "score_death_economy",
        "score_balls_bowled", "score_econ_trend_s1_s2",
        "score_age_factor", "score_bowling_type_fit",
    ]
    cols = [c for c in cols if c in df.columns]
    out  = os.path.join(DELIV, "janakpur_s3_shortlist_matrix.csv")
    df[cols].to_csv(out, index=False)
    print(f"Matrix CSV → {out}")


def write_markdown(df: pd.DataFrame):
    lines = [
        "# Janakpur Bolts — S3 Shortlist Matrix",
        "",
        "## Scoring Methodology",
        "",
        "| Criterion | Weight | Direction |",
        "|---|---|---|",
        "| SOS-adjusted economy | 30% | Lower = better |",
        "| Dot ball % | 20% | Higher = better |",
        "| Death-phase economy | 20% | Lower = better |",
        "| Balls bowled (confidence) | 10% | More = better |",
        "| Economy trend S1→S2 | 10% | Negative = improving |",
        "| Age factor | 5% | Prime age 24–30 |",
        "| Bowling type (NPL fit) | 5% | Pace favoured |",
        "",
        "Each criterion normalised 0–10 (5th–95th percentile clip), then weighted.",
        "",
        "---",
        "",
        "## Top 15 Shortlist Candidates",
        "",
        "| Rank | Player | Score | Tier | SOS Econ | Dot% | Death Econ | Age | Trend |",
        "|---|---|---|---|---|---|---|---|---|",
    ]

    tier_icons = {
        "TIER-1 PRIORITY": "🟢",
        "TIER-2 CONSIDER": "🟡",
        "TIER-3 MONITOR":  "⚪",
    }

    for _, row in df.head(15).iterrows():
        icon  = tier_icons.get(row["shortlist_tier"], "")
        trend = f"{row['econ_trend_s1_s2']:+.2f}" if not pd.isna(row.get("econ_trend_s1_s2")) else "—"
        age   = f"{row['age']:.0f}" if not pd.isna(row.get("age")) else "?"
        death = f"{row['death_econ_raw']:.2f}" if not pd.isna(row.get("death_econ_raw")) else "—"
        dot   = f"{row['dot_ball_pct']:.1f}%" if not pd.isna(row.get("dot_ball_pct")) else "—"
        lines.append(
            f"| {int(row['rank'])} | {row['player_name']} "
            f"| {row['shortlist_score']:.2f} "
            f"| {icon} {row['shortlist_tier']} "
            f"| {row['sos_economy']:.2f} "
            f"| {dot} | {death} | {age} | {trend} |"
        )

    lines += [
        "",
        "---",
        "",
        "## Tier-1 Priority Recruits",
        "",
        "_Players with shortlist score in top quartile — highest value for Janakpur S3._",
        "",
        "| Player | Score | SOS Econ | Death Econ | Age | Bowling Type |",
        "|---|---|---|---|---|---|",
    ]
    tier1 = df[df["shortlist_tier"] == "TIER-1 PRIORITY"]
    for _, row in tier1.iterrows():
        btype = str(row.get("bowling_type", "?") or "?")
        age   = f"{row['age']:.0f}" if not pd.isna(row.get("age")) else "?"
        death = f"{row['death_econ_raw']:.2f}" if not pd.isna(row.get("death_econ_raw")) else "—"
        lines.append(
            f"| {row['player_name']} "
            f"| {row['shortlist_score']:.2f} "
            f"| {row['sos_economy']:.2f} "
            f"| {death} | {age} | {btype} |"
        )

    lines += [
        "",
        "---",
        "",
        "## Criterion Weights Justification",
        "",
        "- **SOS economy (30%)**: Primary performance metric, opponent-strength adjusted.",
        "- **Dot ball % (20%)**: Under-valued in T20 — creates pressure and wicket opportunities.",
        "- **Death economy (20%)**: Overs 16–20 are critical in NPL — decisive phase.",
        "- **Balls bowled (10%)**: More data → lower uncertainty → higher trust in estimate.",
        "- **Trend (10%)**: S1→S2 improvement trajectory matters more than absolute level.",
        "- **Age (5%)**: Prime-age bowlers (24–30) give 2–3 seasons of reliable output.",
        "- **Bowling type (5%)**: Pace marginally favoured at Kathmandu altitude.",
    ]

    out = os.path.join(DELIV, "janakpur_s3_shortlist_top15.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print(f"Markdown report → {out}")


def main():
    df = build_matrix()
    write_csv(df)
    write_markdown(df)

    print(f"\nTotal candidates evaluated: {len(df)}")
    print(f"Tier-1 Priority:  {(df['shortlist_tier']=='TIER-1 PRIORITY').sum()}")
    print(f"Tier-2 Consider:  {(df['shortlist_tier']=='TIER-2 CONSIDER').sum()}")
    print(f"Tier-3 Monitor:   {(df['shortlist_tier']=='TIER-3 MONITOR').sum()}")
    print("\nTop 10:")
    print(df[["rank","player_name","shortlist_score","shortlist_tier","sos_economy"]].head(10).to_string(index=False))


if __name__ == "__main__":
    main()
