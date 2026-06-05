"""Season 3 recommendation engine.

Provides phase-target definitions and role-slot recommendation helpers used
by the S3 recruiting page to produce tactical recruitment guidance.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

import pandas as pd

# Default phase targets (runs per over / economy expectations)
DEFAULT_PHASE_TARGETS: Dict[str, Dict[str, float]] = {
    "Powerplay": {"bat_rpo": 9.5, "bowl_rpo": 7.5},
    "Middle": {"bat_rpo": 8.0, "bowl_rpo": 8.5},
    "Death": {"bat_rpo": 11.0, "bowl_rpo": 9.0},
}


def _map_role_to_phase(role: str) -> List[str]:
    """Map a tactical S3 role to one or more match phases.

    This mapping drives slot-level recommendations (e.g., death specialists -> Death).
    """
    r = role.lower()
    if "powerplay" in r or "opener" in r:
        return ["Powerplay"]
    if "death" in r or "finisher" in r:
        return ["Death"]
    if "middle" in r or "anchor" in r or "controller" in r:
        return ["Middle"]
    if "wicket" in r or "strike" in r:
        # wicket-taking options can span Powerplay and Middle depending on matchup
        return ["Powerplay", "Middle"]
    # default to Middle when unclear
    return ["Middle"]


def build_s3_recommendations(
    form_table: pd.DataFrame, phase_targets: Dict[str, Dict[str, float]] | None = None
) -> Tuple[pd.DataFrame, List[dict]]:
    """Produce role-slot recommendations and a short action report.

    Args:
        form_table: output of `build_player_form_table` / `load_player_form_table`.
        phase_targets: optional override for DEFAULT_PHASE_TARGETS.

    Returns:
        role_summary: DataFrame with tactical role, total players, stable_or_better, mapped_phases, gap
        action_report: list of decision-block dicts (label/text) suitable for UI cards
    """
    if phase_targets is None:
        phase_targets = DEFAULT_PHASE_TARGETS

    if form_table.empty:
        return pd.DataFrame(), [
            {"label": "Insight", "text": "No player form data available."},
            {"label": "Risk", "text": "Unable to compute S3 recommendations without form inputs."},
            {"label": "Recommended Action", "text": "Load parquet inputs and retry."},
        ]

    critical_roles = [
        "Death specialist",
        "Powerplay strike bowler",
        "Finisher (explosive)",
        "Opener (intent)",
        "Middle-overs controller",
    ]

    rows: List[dict] = []
    for role in sorted(set(form_table["recommended_role"]).union(critical_roles)):
        role_df = form_table[form_table["recommended_role"] == role]
        total = len(role_df)
        stable_or_better = int(role_df[role_df["form_band"].isin(["In Form", "Stable"])].shape[0])
        phases = _map_role_to_phase(role)
        # gap heuristic: desired stable coverage per role (defaults tuned for S3)
        desired = 2 if "bowler" in role.lower() or "death" in role.lower() else 1
        gap = max(0, desired - stable_or_better)
        rows.append(
            {
                "s3_role": role,
                "total_players": total,
                "stable_or_better": stable_or_better,
                "mapped_phases": ", ".join(phases),
                "gap": gap,
            }
        )

    role_summary = pd.DataFrame(rows).sort_values(["gap", "stable_or_better", "total_players"], ascending=[False, True, True])

    # Build a short action-oriented report
    insights: List[dict] = []
    total_in_form = int((form_table["form_band"] == "In Form").sum())
    insights.append({"label": "Insight", "text": f"{len(form_table)} players ranked; {total_in_form} in-form players."})

    # Risk block
    high_risk_roles = role_summary[role_summary["gap"] > 0]
    if not high_risk_roles.empty:
        risk_text = (
            "Roles with insufficient stable coverage: "
            + ", ".join(high_risk_roles["s3_role"].tolist())
        )
    else:
        risk_text = "No immediate role coverage risks detected." 

    insights.append({"label": "Risk", "text": risk_text})

    # Recommended Action: produce top 3 recruitment moves
    recs: List[str] = []
    for _, row in high_risk_roles.head(3).iterrows():
        if row["total_players"] == 0:
            recs.append(f"Recruit external {row['s3_role']} (zero current candidates).")
        else:
            recs.append(f"Upgrade or add {row['gap']} stable {row['s3_role']} to meet depth.")

    if not recs:
        recs = ["No immediate recruitment recommended; focus on role execution." ]

    insights.append({"label": "Recommended Action", "text": " ".join(recs)})

    return role_summary.reset_index(drop=True), insights
