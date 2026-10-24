"""Canonical forecast-stage registry (review S13 fix, G1, 2026-10-24).

Problem this solves: the string "P1" historically named TWO different
information sets -- the pre-season expected-XI locks (stored in the
frozen log as stage `P1_preseason_expected_xi`) and the matchday
confirmed-XI horizon (engine contract name "P1", stored by
scripts/lock_matchday.py as `P1_post_XI`). A forecast horizon is part
of the prediction itself, so the two must never share a name.

This module is the single naming layer. It introduces CANONICAL
horizon names and an explicit, total mapping to every stage string
that exists (or can be written) in the frozen log:

    canonical        stored stage string        legacy/contract alias
    ---------------  -------------------------  ---------------------
    P0_PRESEASON     P1_preseason_expected_xi   --
    P1_CONFIRMED_XI  P1_post_XI                 "P1" (engine contract)
    P2_POST_TOSS     P2_post_toss               "P2" (engine contract)
    SIM_SHADOW       SIM_shadow_preseason       -- (shadow SYSTEM)
    INPLAY           -- (no frozen-log stage)   -- (separate SYSTEM)

Rules:
- Locked rows are NEVER rewritten: the frozen log keeps its stored
  strings forever. Canonical names are a reading/display layer.
- New locks keep writing the EXISTING stored strings (via
  stored_stage()), so the log stays internally consistent.
- SIM_SHADOW and INPLAY are systems, not horizons: the simulator is a
  shadow challenger scored separately, and in-play win probability is
  a delivery-level task evaluated by its own harness. They are in the
  registry so every stage string has exactly one home.
- Unknown stage strings raise. A new stage may only appear by being
  registered here first -- an unregistered string in the log is a bug,
  not a new category.
"""
from __future__ import annotations

CANONICAL_STAGES = {
    "P0_PRESEASON": {
        "label": "P0 — Pre-season (expected XI)",
        "kind": "horizon",
        "system": "pre_match",
        "when_issued": "Before the season starts (locked 2026-10-24 for "
                       "all 28 league fixtures).",
        "permitted_information": "Pre-season Elo ratings, player priors, "
                                 "expected XIs from the priors selector, "
                                 "form/rest from completed prior seasons. "
                                 "No toss, no announced XI, no S3 results.",
        "stored_stage": "P1_preseason_expected_xi",
    },
    "P1_CONFIRMED_XI": {
        "label": "P1 — Confirmed XI (pre-toss)",
        "kind": "horizon",
        "system": "pre_match",
        "when_issued": "Matchday, after the official XIs are announced, "
                       "before the toss (~30-60 min before the match).",
        "permitted_information": "Everything in P0, with the expected XI "
                                 "replaced by the announced XI. No toss "
                                 "fields — enforced by the engine contract.",
        "stored_stage": "P1_post_XI",
    },
    "P2_POST_TOSS": {
        "label": "P2 — Post-toss",
        "kind": "horizon",
        "system": "toss_adjusted",
        "when_issued": "Matchday, after the toss, before the first ball.",
        "permitted_information": "Everything in P1 plus toss winner and "
                                 "decision (both required), with the "
                                 "pre-declared chase adjustment.",
        "stored_stage": "P2_post_toss",
    },
    "SIM_SHADOW": {
        "label": "SIM — Shadow simulator",
        "kind": "shadow_system",
        "system": "shadow_simulator",
        "when_issued": "Pre-season (locked 2026-10-24, expected XIs, "
                       "10,000 sims per match).",
        "permitted_information": "Expected XI, priors, ball-by-ball "
                                 "outcome distributions. No toss fields.",
        "stored_stage": "SIM_shadow_preseason",
    },
    "INPLAY": {
        "label": "In-play win probability",
        "kind": "system",
        "system": "in_play",
        "when_issued": "Continuously during a match; never locked in "
                       "the frozen log.",
        "permitted_information": "Current match state only (score, "
                                 "wickets, legal balls, target, innings).",
        "stored_stage": None,
    },
}

# Every stage string that can appear in the frozen log (stored strings
# plus the bare engine-contract aliases) -> its canonical name.
STAGE_TO_CANONICAL = {
    "P1_preseason_expected_xi": "P0_PRESEASON",
    "P1_post_XI": "P1_CONFIRMED_XI",
    "P1": "P1_CONFIRMED_XI",   # engine contract alias; locks as P1_post_XI
    "P2_post_toss": "P2_POST_TOSS",
    "P2": "P2_POST_TOSS",      # engine contract alias; locks as P2_post_toss
    "SIM_shadow_preseason": "SIM_SHADOW",
}

# Canonical name -> the stage string new locks must write (the string
# already used by the existing locked rows of that horizon).
CANONICAL_TO_STAGE = {
    name: spec["stored_stage"] for name, spec in CANONICAL_STAGES.items()
    if spec["stored_stage"] is not None
}

# Display/scoring order for the horizons (systems listed after).
HORIZON_ORDER = ["P0_PRESEASON", "P1_CONFIRMED_XI", "P2_POST_TOSS",
                 "SIM_SHADOW", "INPLAY"]


def canonical_stage(stage: str) -> str:
    """Canonical horizon/system name for a frozen-log stage string.
    Raises ValueError for any unregistered string — scoring and
    display must never silently invent a category."""
    try:
        return STAGE_TO_CANONICAL[stage]
    except KeyError:
        raise ValueError(
            f"unknown prediction stage: {stage!r} — register it in "
            f"src/prediction/stages.py before use") from None


def stored_stage(canonical: str) -> str:
    """The frozen-log stage string that locks for `canonical` must
    write. Raises ValueError for unknown names and for INPLAY, which
    is never locked."""
    if canonical not in CANONICAL_STAGES:
        raise ValueError(f"unknown canonical stage: {canonical!r}")
    stored = CANONICAL_STAGES[canonical]["stored_stage"]
    if stored is None:
        raise ValueError(
            f"canonical stage {canonical!r} has no frozen-log stage "
            f"string (it is not a locked horizon)")
    return stored


def canonical_label(stage_or_canonical: str) -> str:
    """Human-readable label for a stored stage string or a canonical
    name. Raises ValueError on anything unregistered."""
    name = (stage_or_canonical if stage_or_canonical in CANONICAL_STAGES
            else canonical_stage(stage_or_canonical))
    return CANONICAL_STAGES[name]["label"]


def mapping_note() -> str:
    """One-line-per-horizon mapping of canonical names to the stage
    strings stored in the frozen log (for dashboards/runbooks, so the
    stored strings are shown exactly once alongside the labels)."""
    lines = []
    for name in HORIZON_ORDER:
        spec = CANONICAL_STAGES[name]
        stored = spec["stored_stage"]
        lines.append(f"{name} (stored as {stored})" if stored
                     else f"{name} (not stored in the frozen log)")
    return "; ".join(lines)
