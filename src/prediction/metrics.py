"""Proper scoring metrics for probabilistic match predictions."""
import numpy as np

EPS = 1e-15


def log_loss(p, y):
    p = np.clip(np.asarray(p, float), EPS, 1 - EPS)
    y = np.asarray(y, float)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def brier(p, y):
    return float(np.mean((np.asarray(p, float) - np.asarray(y, float)) ** 2))


def accuracy(p, y):
    return float(np.mean((np.asarray(p, float) >= 0.5) == (np.asarray(y, float) >= 0.5)))


def score_all(p, y):
    return {"n": int(len(y)), "accuracy": accuracy(p, y),
            "log_loss": log_loss(p, y), "brier": brier(p, y)}


def per_match_log_loss(p, y):
    """Log-loss contribution of each match (elementwise)."""
    p = np.clip(np.asarray(p, float), EPS, 1 - EPS)
    y = np.asarray(y, float)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def per_match_correct(p, y):
    """1.0 where the favoured team won, else 0.0 (elementwise)."""
    return ((np.asarray(p, float) >= 0.5)
            == (np.asarray(y, float) >= 0.5)).astype(float)


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
