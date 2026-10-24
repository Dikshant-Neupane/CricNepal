"""Proper scoring metrics for probabilistic match predictions."""
import numpy as np

EPS = 1e-15


def log_loss(p, y):
    p = np.clip(np.asarray(p, float), EPS, 1 - EPS)
    y = np.asarray(y, float)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def brier(p, y):
    return float(np.mean((np.asarray(p, float) - np.asarray(y, float)) ** 2))


TIE_RULE = ("Uniform tie rule (F2 audit, 2026-10-24): a prediction of "
            "exactly p = 0.5 picks team_1 by convention and is scored "
            "normally (correct iff team_1 won). Applies to every model "
            "and baseline via accuracy()/per_match_correct(); ratings "
            "exactly equal produce p = 0.5 and follow the same rule.")


def accuracy(p, y):
    """Share of matches where the favoured team won.

    The pick is team_1 iff p >= 0.5 -- see TIE_RULE: an exact 0.5 is a
    team_1 pick by convention, never excluded and never half-credited.
    """
    return float(np.mean((np.asarray(p, float) >= 0.5) == (np.asarray(y, float) >= 0.5)))


def score_all(p, y):
    return {"n": int(len(y)), "accuracy": accuracy(p, y),
            "log_loss": log_loss(p, y), "brier": brier(p, y)}


def coin_baseline_metrics(n: int) -> dict:
    """The coin-flip baseline, by construction (F2 audit, 2026-10-24).

    The coin predicts p = 0.5 for every match, so its log-loss is
    ln(2) and its Brier score 0.25 BY CONSTRUCTION, on any match set.
    Its accuracy is NOT a measured quantity: under any deterministic
    tie rule an all-0.5 predictor degenerates to a constant pick (with
    the uniform rule, 'always team_1'), so a computed 'coin accuracy'
    merely restates the team_1 win share of the sample (on S2 that
    produced the misleading 0.34375 = 11/32). Accuracy is therefore
    null here; the expected accuracy of a fair coin is 0.5 by symmetry.
    Never emit a pseudo-measured coin accuracy again.
    """
    return {"n": int(n), "accuracy": None,
            "log_loss": float(np.log(2.0)), "brier": 0.25,
            "accuracy_note": "Not a measured quantity: the coin predicts "
                             "p=0.5 for every match, so its accuracy is "
                             "0.5 in expectation by symmetry. A computed "
                             "value under a deterministic tie rule would "
                             "just restate the sample's team_1 win share "
                             "(S2: 0.34375), which is why it is null."}


def per_match_log_loss(p, y):
    """Log-loss contribution of each match (elementwise)."""
    p = np.clip(np.asarray(p, float), EPS, 1 - EPS)
    y = np.asarray(y, float)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def per_match_correct(p, y):
    """1.0 where the favoured team won, else 0.0 (elementwise).
    Same uniform tie rule as accuracy(): p >= 0.5 favours team_1."""
    return ((np.asarray(p, float) >= 0.5)
            == (np.asarray(y, float) >= 0.5)).astype(float)


OUTCOME_SCORED = "scored"
OUTCOME_EXCLUDED_NO_RESULT = "excluded_no_result"
OUTCOME_EXCLUDED_TIED = "excluded_tied_no_decider"


def classify_outcome(match) -> tuple:
    """Classify a completed match for prediction scoring, under the
    outcome rules frozen before Season 3 (docs/PREDICTION_SYSTEM.md,
    'Outcome rules for scoring'; review §4.2):

      - The target is the official match winner as recorded by
        cricsheet (the ingested `winner_name`).
      - A super-over decider counts as a win for the super-over
        winner: if the source records the decider in `winner_name`
        (or an `eliminator` field is present naming a team), the match
        is SCORED with that winner.
      - A DLS / par-score result counts as a win for the officially
        declared winner (winner_name set) -> SCORED.
      - A match tied with no decider, abandoned, or with no result is
        EXCLUDED from scoring -- never scored as 0.5, never silently
        dropped; the reason is returned with the classification.

    `match` is a mapping/Series with at least 'winner_name' and
    optionally 'result_status' / 'eliminator'. Returns
    (classification, winner_name_or_None, reason).
    """
    def _get(key):
        try:
            v = match.get(key)
        except AttributeError:
            return None
        return None if v is None or (isinstance(v, float) and v != v) else v

    winner = _get("winner_name")
    if isinstance(winner, str) and winner.strip():
        return OUTCOME_SCORED, winner, ""
    eliminator = _get("eliminator")
    if isinstance(eliminator, str) and eliminator.strip():
        # Tied match decided by a super over: the eliminator winner is
        # the official winner for scoring purposes.
        return OUTCOME_SCORED, eliminator, ""
    status = _get("result_status")
    status = status.strip().lower() if isinstance(status, str) else ""
    if status == "tie":
        return (OUTCOME_EXCLUDED_TIED, None,
                "match tied with no decider recorded (no winner in source)")
    if status:
        return (OUTCOME_EXCLUDED_NO_RESULT, None,
                f"no result (result_status={status!r}); no winner recorded")
    return (OUTCOME_EXCLUDED_NO_RESULT, None,
            "no winner recorded in source (abandoned / no result)")


def paired_bootstrap(diffs, n_resamples: int = 10000, seed: int = 42,
                     lower_is_better: bool = True) -> dict:
    """Paired bootstrap over matches of a per-match difference array
    (model A minus model B). Resamples matches with replacement using a
    FIXED seed, so results are exactly reproducible. Returns the mean
    difference, a percentile 95% CI, and the share of bootstrap means on
    the 'A is better' side of zero (below zero when lower is better,
    e.g. log-loss differences; above zero for accuracy differences)."""
    d = np.asarray(diffs, float)
    n = len(d)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_resamples, n))
    means = d[idx].mean(axis=1)
    better = (means < 0) if lower_is_better else (means > 0)
    return {"n_matches": int(n), "n_resamples": int(n_resamples),
            "seed": int(seed), "mean_diff": float(d.mean()),
            "ci_low": float(np.percentile(means, 2.5)),
            "ci_high": float(np.percentile(means, 97.5)),
            "prob_a_better": float(better.mean()),
            "ci_includes_zero": bool(np.percentile(means, 2.5) <= 0.0
                                     <= np.percentile(means, 97.5))}
