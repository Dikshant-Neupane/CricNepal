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
