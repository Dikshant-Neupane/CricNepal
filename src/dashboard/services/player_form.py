"""Player form scoring and role guidance for Season 3 selection."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from src.config.paths import PARQUET_DIR
from src.dashboard.services.metrics import COMPETITION_WEIGHTS

PLAYER_INNINGS_PATH = PARQUET_DIR / "player_innings.parquet"
MATCHES_PATH = PARQUET_DIR / "matches.parquet"
DEFAULT_TEAM = "Janakpur Bolts"
MIN_MATCHES_FOR_FORM = 3


def _empty_form_table() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "player_name",
            "primary_role",
            "recent_matches",
            "raw_form_score",
            "weighted_form_score",
            "form_band",
            "recommended_role",
            "role_recommendation",
            "avg_runs",
            "avg_strike_rate",
            "avg_wickets",
            "avg_economy",
            "s1_s2_reference",
        ]
    )


def load_player_form_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load player innings and match metadata from parquet."""
    if not PLAYER_INNINGS_PATH.exists() or not MATCHES_PATH.exists():
        return pd.DataFrame(), pd.DataFrame()

    return pd.read_parquet(PLAYER_INNINGS_PATH), pd.read_parquet(MATCHES_PATH)


def _competition_weight(name: Any) -> float:
    if pd.isna(name):
        return 0.05
    return float(COMPETITION_WEIGHTS.get(str(name), 0.05))


def _make_weight_fn(weights: dict[str, float]):
    """Return a callable that maps competition name → normalised weight."""
    total = sum(weights.values()) or 1.0
    normalised = {k: v / total for k, v in weights.items()}
    def fn(name: Any) -> float:
        if pd.isna(name):
            return 0.05
        return float(normalised.get(str(name), 0.05))
    return fn


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _batting_match_score(row: pd.Series) -> float | None:
    runs = float(row.get("runs_scored", 0) or 0)
    balls = float(row.get("balls_faced", 0) or 0)
    strike_rate = float(row.get("strike_rate", 0) or 0)
    if balls <= 0 and runs <= 0:
        return None

    runs_component = _clamp(runs / 40.0) * 60.0
    strike_component = _clamp(strike_rate / 160.0) * 40.0
    return round(runs_component + strike_component, 1)


def _bowling_match_score(row: pd.Series) -> float | None:
    balls_bowled = float(row.get("balls_bowled", 0) or 0)
    wickets = float(row.get("wickets_taken", 0) or 0)
    economy = row.get("economy_rate", None)
    economy = float(economy) if pd.notna(economy) else None
    if balls_bowled <= 0 and wickets <= 0:
        return None

    wickets_component = _clamp(wickets / 3.0) * 55.0
    economy_component = 20.0
    if economy is not None:
        economy_component = _clamp((9.5 - economy) / 4.5) * 45.0
    return round(wickets_component + economy_component, 1)


def _overall_match_score(row: pd.Series) -> float:
    batting_score = _batting_match_score(row)
    bowling_score = _bowling_match_score(row)
    scores = [score for score in [batting_score, bowling_score] if score is not None]
    if not scores:
        return 0.0
    return round(sum(scores) / len(scores), 1)


def _standardize_role(player_role: Any, batting_matches: int, bowling_matches: int) -> str:
    role_text = str(player_role or "").lower()
    if "all" in role_text:
        return "All-rounder"
    if "bowl" in role_text:
        return "Bowler"
    if "keeper" in role_text or "bat" in role_text:
        return "Batter"
    if batting_matches > 0 and bowling_matches > 0:
        return "All-rounder"
    if bowling_matches > batting_matches:
        return "Bowler"
    return "Batter"


def classify_form_band(score: float) -> str:
    """Classify a player into a selection-ready form band.

    Thresholds calibrated for NPL innings volume (8-17 innings per player).
    With limited data, scores naturally cluster in the 40-65 range.
    """
    if score >= 60.0:
        return "In Form"
    if score >= 48.0:
        return "Stable"
    if score >= 35.0:
        return "Risky"
    return "Out of Form"


def _season_reference(role: str, s1: pd.DataFrame, s2: pd.DataFrame) -> str:
    if s1.empty or s2.empty:
        return "S1/S2 delta unavailable; lean on recent T20 form." 

    if role == "Bowler":
        s1_econ = float(s1["economy_rate"].fillna(0).replace(0, pd.NA).dropna().mean()) if not s1.empty else 0.0
        s2_econ = float(s2["economy_rate"].fillna(0).replace(0, pd.NA).dropna().mean()) if not s2.empty else 0.0
        s1_wkts = float(s1["wickets_taken"].fillna(0).mean())
        s2_wkts = float(s2["wickets_taken"].fillna(0).mean())
        return (
            f"S2 economy {s2_econ:.2f} vs S1 {s1_econ:.2f} "
            f"({s2_econ - s1_econ:+.2f}); wickets/match {s2_wkts:.2f} vs {s1_wkts:.2f}."
        )

    s1_sr = float(s1["strike_rate"].fillna(0).mean())
    s2_sr = float(s2["strike_rate"].fillna(0).mean())
    s1_runs = float(s1["runs_scored"].fillna(0).mean())
    s2_runs = float(s2["runs_scored"].fillna(0).mean())
    return (
        f"S2 strike rate {s2_sr:.1f} vs S1 {s1_sr:.1f} "
        f"({s2_sr - s1_sr:+.1f}); runs/match {s2_runs:.1f} vs {s1_runs:.1f}."
    )


def _recommended_role(
    role: str,
    avg_runs: float,
    avg_sr: float,
    avg_wickets: float,
    avg_econ: float,
    avg_balls_faced: float,
) -> str:
    """Assign granular S3 role based on recent performance profile."""
    if role == "Bowler":
        # Phase-inferred bowling roles based on economy and wicket-taking
        if avg_econ <= 7.0 and avg_wickets >= 0.9:
            return "Death specialist"  # Precision required in high-pressure overs
        if avg_econ <= 7.5 and avg_wickets >= 1.0:
            return "Powerplay strike bowler"  # Early wickets with economy control
        if avg_econ <= 8.3:
            return "Middle-overs controller"  # Stem run flow in rotation phase
        if avg_wickets >= 1.2:
            return "Wicket-taking option"  # High wicket rate, economy secondary
        return "Matchup / backup bowler"  # Limited role or situational use
    
    if role == "All-rounder":
        if avg_runs >= 22 and avg_wickets >= 1.0 and avg_econ <= 8.5:
            return "Primary all-rounder"  # Dual threat in both disciplines
        if avg_runs >= 18 and avg_wickets >= 0.7:
            return "Batting all-rounder"  # Batting primary, bowling support
        if avg_wickets >= 1.0 and avg_econ <= 8.5:
            return "Bowling all-rounder"  # Bowling primary, batting depth
        return "Flex utility"  # Situational dual role
    
    # Batter roles inferred from balls faced and strike patterns
    if avg_balls_faced >= 25:  # Substantial innings length
        if avg_sr >= 140:
            return "Opener (intent)"  # High SR with volume = powerplay aggressor
        if avg_sr >= 125:
            return "Opener (balanced)"  # Good SR with stability
        if avg_runs >= 28:
            return "No. 3 anchor"  # High-volume run accumulator
        return "Top-order batter"
    
    if avg_balls_faced >= 18:  # Medium innings length
        if avg_sr >= 135 and avg_runs >= 20:
            return "Middle-order accelerator"  # Strike rotation + boundaries
        if avg_runs >= 22:
            return "Middle-order anchor"  # Stabilizer in overs 10-16
        return "Middle-order batter"
    
    # Low balls faced = finishing or depth role
    if avg_sr >= 145:
        return "Finisher (explosive)"  # High-impact cameos
    if avg_sr >= 120:
        return "Finisher (rotator)"  # Rotation-focused closer
    return "Lower-order / depth"  # Limited batting output


def _role_recommendation(role: str, band: str, recommended_role: str, season_ref: str) -> str:
    """Generate tactical S3 selection guidance based on form band and recommended role."""
    if band == "In Form":
        action = f"Retain as {recommended_role.lower()} for S3."
    elif band == "Stable":
        action = f"Keep in core rotation as {recommended_role.lower()}, but monitor role execution."
    elif band == "Risky":
        action = f"Carry only with clearly defined {recommended_role.lower()} role and matchup protection."
    else:
        action = f"Do not lock into starting XI until {recommended_role.lower()} output recovers."

    # Tactical guidance based on granular role
    role_lower = recommended_role.lower()
    if "death specialist" in role_lower:
        tactic = "Reserve for overs 17-20; prioritize yorkers and wide variations."
    elif "powerplay" in role_lower:
        tactic = "Deploy in overs 1-6; target early wickets with attacking lengths."
    elif "middle-overs controller" in role_lower:
        tactic = "Use in overs 7-15 to stem run flow; focus on hard lengths and change-ups."
    elif "wicket-taking" in role_lower:
        tactic = "Deploy when breakthrough needed; accept higher economy for strike capability."
    elif "opener" in role_lower:
        tactic = "Target 40-50 runs in powerplay with intent on scoring opportunities."
    elif "no. 3" in role_lower or "anchor" in role_lower:
        tactic = "Stabilize innings through middle overs; rotate strike and punish poor lengths."
    elif "finisher" in role_lower:
        tactic = "Reserve for overs 16-20; prioritize boundary hitting and run-chase finishing."
    elif "all-rounder" in role_lower:
        tactic = "Balance batting and bowling loads; use as tactical flexibility asset."
    else:
        tactic = "Define specific match role before selection to avoid generic depth usage."

    return f"{action} {season_ref} {tactic}"


def build_player_form_table(
    player_innings: pd.DataFrame,
    matches: pd.DataFrame,
    team_name: str = DEFAULT_TEAM,
    n_recent: int = 8,
    min_matches: int = MIN_MATCHES_FOR_FORM,
    competition_weights: dict[str, float] | None = None,
) -> pd.DataFrame:
    """Build raw and weighted player form rankings with role guidance."""
    if player_innings.empty or matches.empty:
        return _empty_form_table()

    meta_cols = [
        column
        for column in ["match_id", "match_date", "season", "tournament_name", "winner_name"]
        if column in matches.columns
    ]
    merged = player_innings.merge(matches[meta_cols], on="match_id", how="left")
    merged = merged[merged["team_name"] == team_name].copy()
    if merged.empty:
        return _empty_form_table()

    merged["match_date"] = pd.to_datetime(merged.get("match_date"), errors="coerce")
    merged["competition_name"] = merged.get("tournament_name").fillna("Unknown")
    merged["match_score"] = merged.apply(_overall_match_score, axis=1)
    merged["competition_weight"] = merged["competition_name"].map(
        _make_weight_fn(competition_weights if competition_weights is not None else COMPETITION_WEIGHTS)
    )

    rows: list[dict[str, Any]] = []
    for player_name, group in merged.groupby("player_name"):
        recent = group.sort_values("match_date", ascending=False).head(n_recent).copy()
        if len(recent) < min_matches:
            continue

        batting_matches = int((recent["balls_faced"].fillna(0) > 0).sum())
        bowling_matches = int((recent["balls_bowled"].fillna(0) > 0).sum())
        primary_role = _standardize_role(recent["player_role"].mode().iloc[0] if not recent["player_role"].mode().empty else None, batting_matches, bowling_matches)

        raw_form_score = round(float(recent["match_score"].mean()), 1)
        weighted_total = float((recent["match_score"] * recent["competition_weight"]).sum())
        total_weight = float(recent["competition_weight"].sum())
        weighted_form_score = round(weighted_total / total_weight, 1) if total_weight else raw_form_score
        form_band = classify_form_band(weighted_form_score)

        avg_runs = round(float(recent["runs_scored"].fillna(0).mean()), 1)
        avg_strike_rate = round(float(recent["strike_rate"].fillna(0).mean()), 1)
        avg_balls_faced = round(float(recent["balls_faced"].fillna(0).mean()), 1)
        avg_wickets = round(float(recent["wickets_taken"].fillna(0).mean()), 2)
        avg_economy = recent["economy_rate"].replace(0, pd.NA).dropna()
        avg_economy_value = round(float(avg_economy.mean()), 2) if not avg_economy.empty else 0.0

        season_ref = _season_reference(
            primary_role,
            group[group["season"] == "S1"],
            group[group["season"] == "S2"],
        )
        recommended_role = _recommended_role(
            primary_role, avg_runs, avg_strike_rate, avg_wickets, avg_economy_value, avg_balls_faced
        )
        role_recommendation = _role_recommendation(primary_role, form_band, recommended_role, season_ref)

        rows.append(
            {
                "player_name": player_name,
                "primary_role": primary_role,
                "recent_matches": len(recent),
                "raw_form_score": raw_form_score,
                "weighted_form_score": weighted_form_score,
                "form_band": form_band,
                "recommended_role": recommended_role,
                "role_recommendation": role_recommendation,
                "avg_runs": avg_runs,
                "avg_strike_rate": avg_strike_rate,
                "avg_balls_faced": avg_balls_faced,
                "avg_wickets": avg_wickets,
                "avg_economy": avg_economy_value,
                "s1_s2_reference": season_ref,
            }
        )

    if not rows:
        return _empty_form_table()

    result = pd.DataFrame(rows)
    return result.sort_values(
        ["weighted_form_score", "raw_form_score", "player_name"],
        ascending=[False, False, True],
    ).reset_index(drop=True)


def load_player_form_table(
    team_name: str = DEFAULT_TEAM,
    n_recent: int = 8,
    min_matches: int = MIN_MATCHES_FOR_FORM,
    competition_weights: dict[str, float] | None = None,
) -> pd.DataFrame:
    """Convenience loader for the S3 selection dashboard."""
    player_innings, matches = load_player_form_inputs()
    return build_player_form_table(
        player_innings=player_innings,
        matches=matches,
        team_name=team_name,
        n_recent=n_recent,
        min_matches=min_matches,
        competition_weights=competition_weights,
    )


def summarize_selection_decisions(form_table: pd.DataFrame) -> list[dict[str, str]]:
    """Generate a compact decision summary for the dashboard header."""
    if form_table.empty:
        return [
            {
                "label": "Status",
                "text": "No player form data available for Season 3 selection decisions.",
                "type": "warning",
            }
        ]

    in_form = int((form_table["form_band"] == "In Form").sum())
    risky = int(form_table["form_band"].isin(["Risky", "Out of Form"]).sum())
    top_player = form_table.iloc[0]
    top_role = top_player["recommended_role"]

    return [
        {
            "label": "Insight",
            "text": f"{in_form} players are in form. Top current option: {top_player['player_name']} as {top_role.lower()} ({top_player['weighted_form_score']:.1f}).",
            "type": "success",
        },
        {
            "label": "Risk",
            "text": f"{risky} players sit in Risky/Out of Form bands, so S3 selection should protect unstable roles rather than copy the full S2 core.",
            "type": "warning",
        },
        {
            "label": "Recommended Action",
            "text": "Select the XI from weighted form first, then use S1/S2 deltas to decide whether each player gets a primary role or only matchup cover.",
            "type": "neutral",
        },
    ]