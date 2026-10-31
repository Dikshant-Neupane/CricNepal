"""Opponent-specific plan generator (plan task 6.3, criteria S2/S3).

Unlike the frozen preseason opposition page (which reads a static
forecast table and takes no opponent argument), this generator takes
the opponent as an input and builds Janakpur's bowling and batting
plans from THAT opponent's priors phase data plus Janakpur's
eligible squad (the cap-legal expected XI from the engine selector).

Every plan entry follows the evidence structure:
    observation -> evidence (n, league baseline, interval)
    -> limitation -> possible action -> alternative.

Discipline (S2, S4):
- Evidence is labelled Limited (<30 effective balls), Moderate
  (30-120) or Strong (>120). No entry based on Limited evidence
  carries a targeting action or any "weakness" label -- it says so.
- No line, length, delivery-type or style claims anywhere: plans
  name WHO bowls/bats and in WHICH phase, never HOW to bowl.
- No causal language: actions are options ("can", "is an option"),
  never predicted outcomes.
- Intervals use the same documented normal partial-pooling form as
  the priors build (plan 6.2): sd = sqrt(league_mean / (n + k)).

This module is deliberately NOT wired into the frozen opposition
page; rewiring is a merge-time WAIVER-B decision (docs/WORKLOG.md).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

PHASES = ("powerplay", "middle", "death")
LIMITED_MAX = 30
STRONG_MIN = 120
K_BAT = 150.0
K_BOWL = 120.0

GLOBAL_LIMITATIONS = [
    "Priors are pre-season estimates built from S1/S2 and external "
    "league history; they describe past scoring rates, not future "
    "outcomes, and they do not update for in-season form.",
    "Phase samples for individual players are often small; every "
    "entry labels its own evidence and Limited entries carry no "
    "targeting action.",
    "Plans name personnel and phases only; how any bowler delivers "
    "the ball is outside their scope (criterion S4).",
]


def evidence_label(n: float) -> str:
    if n < LIMITED_MAX:
        return "Limited"
    if n <= STRONG_MIN:
        return "Moderate"
    return "Strong"


def _interval(estimate: float, n: float, league_mean: float, k: float,
              per_over: bool = False):
    sd = float(np.sqrt(max(league_mean, 0.0) / (n + k)))
    if per_over:
        sd *= 6.0
    return (round(max(0.0, estimate - 1.96 * sd), 3),
            round(estimate + 1.96 * sd, 3))


def _weighted_mean(values: pd.Series, weights: pd.Series) -> float:
    w = weights.fillna(0.0)
    if w.sum() <= 0:
        return float("nan")
    return float((values.fillna(0.0) * w).sum() / w.sum())


def _league_baselines(priors: pd.DataFrame) -> dict:
    out = {}
    for ph in PHASES:
        out[("bat", ph)] = _weighted_mean(
            priors[f"prior_bat_rpb_{ph}"], priors[f"bat_balls_eff_{ph}"])
        out[("bowl", ph)] = _weighted_mean(
            priors[f"prior_bowl_econ_{ph}"], priors[f"bowl_balls_eff_{ph}"])
    return out


def _phase_subjects(frame: pd.DataFrame, kind: str, phase: str,
                    top: int = 3) -> pd.DataFrame:
    n_col = f"{kind}_balls_eff_{phase}"
    sub = frame[frame[n_col].fillna(0) > 0]
    return sub.sort_values(n_col, ascending=False).head(top)


def _entry(area, phase, observation, n, baseline, estimate, interval,
           limitation, action, alternative):
    return {
        "area": area,
        "phase": phase,
        "observation": observation,
        "evidence": {
            "n_balls": int(round(float(n))),
            "baseline": round(float(baseline), 3),
            "estimate": round(float(estimate), 3),
            "interval": list(interval) if interval else None,
            "label": evidence_label(n),
        },
        "limitation": limitation,
        "action": action,
        "alternative": alternative,
    }


def _no_action_entry(area, phase, observation, n, baseline, estimate,
                     interval):
    return _entry(
        area, phase, observation, n, baseline, estimate, interval,
        "Evidence is Limited (fewer than 30 effective balls): no "
        "targeting judgement is made on this sample.",
        "No phase-specific change is justified on this evidence; "
        "use the standard plan for this phase.",
        "Revisit once the announced XIs or a larger sample changes "
        "the evidence.")


def generate_opposition_plan(opponent: str, priors: pd.DataFrame,
                             janakpur_team: str = "Janakpur Bolts",
                             approach: pd.DataFrame | None = None,
                             head_to_head: pd.DataFrame | None = None
                             ) -> dict:
    """Build the plan dict for one opponent from the priors table.

    priors: the player_priors frame (phase columns + is_overseas).
    approach / head_to_head: optional data/approach frames.
    """
    from src.prediction import engine

    opp = priors[priors["team"] == opponent]
    if not len(opp):
        raise ValueError(f"no priors rows for opponent {opponent!r}")
    jan = priors[priors["team"] == janakpur_team]
    if not len(jan):
        raise ValueError(f"no priors rows for {janakpur_team!r}")
    xi_keys = engine.select_expected_xi(jan)
    jan_xi = jan[jan["player_key"].isin(xi_keys)]
    base = _league_baselines(priors)

    bowling_plan, batting_plan = [], []
    for ph in PHASES:
        # --- Janakpur bowling vs the opponent's phase batting
        subs = _phase_subjects(opp, "bat", ph)
        n = float(subs[f"bat_balls_eff_{ph}"].sum()) if len(subs) else 0.0
        est = (_weighted_mean(subs[f"prior_bat_rpb_{ph}"],
                              subs[f"bat_balls_eff_{ph}"])
               if len(subs) else float("nan"))
        b_base = base[("bat", ph)]
        iv = _interval(est, n, b_base, K_BAT) if n > 0 else None
        names = ", ".join(subs["canonical_name"]) if len(subs) else "none"
        obs = (f"In the {ph}, {opponent}'s most-used batters "
               f"({names}) score at {est:.3f} runs per ball against a "
               f"league baseline of {b_base:.3f}.")
        jan_bowl = _phase_subjects(jan_xi, "bowl", ph, top=2)
        jan_names = ", ".join(
            f"{r.canonical_name} ({getattr(r, f'prior_bowl_econ_{ph}'):.2f} "
            f"econ, {int(getattr(r, f'bowl_balls_eff_{ph}'))} balls)"
            for r in jan_bowl.itertuples()) or "the standard rotation"
        if evidence_label(n) == "Limited" or iv is None:
            bowling_plan.append(_no_action_entry(
                "bowling", ph, obs, n, b_base, est, iv))
        elif iv[0] > b_base:
            bowling_plan.append(_entry(
                "bowling", ph, obs, n, b_base, est, iv,
                "The interval sits above the baseline, but phase "
                "samples still aggregate several batters and two "
                "seasons of history.",
                f"Prioritise {jan_names} in the {ph}: they are "
                f"Janakpur's lowest-economy options for the phase in "
                f"which {opponent} scores fastest.",
                "If early wickets fall, one of them can be held back "
                "for the death overs instead."))
        elif iv[1] < b_base:
            bowling_plan.append(_entry(
                "bowling", ph, obs, n, b_base, est, iv,
                "The interval sits below the baseline; this describes "
                "scoring rate only, not a defect in the opponent's "
                "batting.",
                f"The standard rotation is acceptable in the {ph}; "
                f"Janakpur's premium options ({jan_names}) can be "
                f"preserved for phases where {opponent} scores "
                f"faster.",
                "If the match situation demands wickets, the premium "
                "options can still be used here."))
        else:
            bowling_plan.append(_entry(
                "bowling", ph, obs, n, b_base, est, iv,
                "The interval overlaps the league baseline: no clear "
                "phase edge in either direction.",
                f"No phase change is indicated against {opponent} "
                f"in the {ph}: their estimate ({est:.3f} rpb) sits "
                f"inside the baseline interval, and {jan_names} "
                f"remain the default options.",
                "Match the choice to the batters at the crease on "
                "the day."))

        # --- Janakpur batting vs the opponent's phase bowling
        subs_b = _phase_subjects(opp, "bowl", ph)
        nb = (float(subs_b[f"bowl_balls_eff_{ph}"].sum())
              if len(subs_b) else 0.0)
        est_b = (_weighted_mean(subs_b[f"prior_bowl_econ_{ph}"],
                                subs_b[f"bowl_balls_eff_{ph}"])
                 if len(subs_b) else float("nan"))
        bo_base = base[("bowl", ph)]
        iv_b = (_interval(est_b, nb, bo_base / 6.0, K_BOWL,
                          per_over=True) if nb > 0 else None)
        names_b = (", ".join(subs_b["canonical_name"])
                   if len(subs_b) else "none")
        obs_b = (f"In the {ph}, {opponent}'s most-used bowlers "
                 f"({names_b}) concede at {est_b:.2f} per over "
                 f"against a league baseline of {bo_base:.2f}.")
        jan_bat = _phase_subjects(jan_xi, "bat", ph, top=2)
        jan_bat_names = ", ".join(
            f"{r.canonical_name} ({getattr(r, f'prior_bat_rpb_{ph}'):.3f} "
            f"rpb, {int(getattr(r, f'bat_balls_eff_{ph}'))} balls)"
            for r in jan_bat.itertuples()) or "the set batters"
        if evidence_label(nb) == "Limited" or iv_b is None:
            batting_plan.append(_no_action_entry(
                "batting", ph, obs_b, nb, bo_base, est_b, iv_b))
        elif iv_b[0] > bo_base:
            batting_plan.append(_entry(
                "batting", ph, obs_b, nb, bo_base, est_b, iv_b,
                "An expensive phase on past evidence is an "
                "opportunity, not a guarantee: conditions and the "
                "announced XI can move it.",
                f"Janakpur's strongest {ph} scorers ({jan_bat_names}) "
                f"can look to bat at their usual rate or above in "
                f"this phase rather than consolidating by default.",
                "If wickets fall early in the phase, consolidation "
                "remains the fallback."))
        elif iv_b[1] < bo_base:
            batting_plan.append(_entry(
                "batting", ph, obs_b, nb, bo_base, est_b, iv_b,
                "The interval sits below the baseline economy; this "
                "phase has historically been tightly bowled by this "
                "opponent.",
                f"Patience is an option in the {ph}: {jan_bat_names} "
                f"can prioritise keeping wickets for phases where "
                f"scoring has come faster.",
                "If a set batter is in, their usual rate remains "
                "available; the plan does not require passivity."))
        else:
            batting_plan.append(_entry(
                "batting", ph, obs_b, nb, bo_base, est_b, iv_b,
                "The interval overlaps the league baseline: no clear "
                "phase edge in either direction.",
                f"Bat the {ph} on its merits against {opponent}: "
                f"their phase economy estimate ({est_b:.2f}) sits "
                f"inside the baseline interval, so no targeting call "
                f"is made.",
                "Reassess against the announced XI on match day."))

    team_level = []
    if approach is not None and len(approach):
        row = approach[approach["team"] == opponent]
        if len(row):
            r = row.iloc[0]
            team_level.append({
                "observation": (
                    f"Across {int(r['matches'])} S1/S2 matches, "
                    f"{opponent} won the toss and fielded first in "
                    f"{float(r['toss_field_pct']):.0f}% of tosses won; "
                    f"they won {float(r['bat_first_win_pct']):.1f}% "
                    f"batting first (n={int(r['bat_first_n'])}) and "
                    f"{float(r['chase_win_pct']):.1f}% chasing "
                    f"(n={int(r['chase_n'])})."),
                "evidence": {"n_matches": int(r["matches"]),
                             "label": evidence_label(r["matches"])},
                "limitation": "Match-count evidence over two seasons "
                              "is thin and mixes squads and venues.",
                "action": "No toss instruction follows from samples "
                          "this size; treat as context only.",
                "alternative": "Decide the toss on pitch and weather "
                               "on the day.",
            })
    if head_to_head is not None and len(head_to_head):
        h = head_to_head[((head_to_head["team_a"] == opponent)
                          & (head_to_head["team_b"] == janakpur_team))
                         | ((head_to_head["team_b"] == opponent)
                            & (head_to_head["team_a"] == janakpur_team))]
        if len(h):
            r = h.iloc[0]
            jan_wins = (int(r["b_wins"]) if r["team_a"] == opponent
                        else int(r["a_wins"]))
            team_level.append({
                "observation": (
                    f"Head-to-head in S1/S2: {int(r['matches'])} "
                    f"matches, {janakpur_team} won {jan_wins}."),
                "evidence": {"n_matches": int(r["matches"]),
                             "label": evidence_label(r["matches"])},
                "limitation": "Two meetings cannot support a matchup "
                              "claim; recorded for completeness only.",
                "action": "None. No plan element rests on the "
                          "head-to-head record.",
                "alternative": "None.",
            })

    return {
        "opponent": opponent,
        "janakpur_team": janakpur_team,
        "janakpur_expected_xi": xi_keys,
        "bowling_plan": bowling_plan,
        "batting_plan": batting_plan,
        "team_level": team_level,
        "limitations": list(GLOBAL_LIMITATIONS),
    }
