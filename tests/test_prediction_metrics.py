"""Hand-example tests for src/prediction/metrics.py (plan 5.1, V2).

Definitions under test (master prompt Section 5):
  Brier    = mean((p - y)^2)
  Log loss = -mean(y ln p + (1-y) ln(1-p)), p clipped to [1e-6, 1-1e-6]
  Accuracy under the module's documented uniform tie rule (p >= 0.5
  picks team_1, scored normally).
"""
import numpy as np
import pytest

from src.prediction import metrics as pm


def test_brier_hand_example():
    assert pm.brier([0.5], [1]) == pytest.approx(0.25)
    assert pm.brier([0.9, 0.1], [1, 0]) == pytest.approx(0.01)
    assert pm.brier([1.0, 0.0], [1, 0]) == pytest.approx(0.0)


def test_log_loss_hand_example():
    assert pm.log_loss([0.5], [1]) == pytest.approx(np.log(2))
    assert pm.log_loss([0.5, 0.5], [1, 0]) == pytest.approx(np.log(2))
    assert pm.log_loss([0.8], [1]) == pytest.approx(-np.log(0.8))


def test_log_loss_clipping_is_1e_6():
    # A certain-and-right prediction must score -ln(1 - 1e-6), which is
    # distinguishable from the old 1e-15 clip (~0) and from no clip (0).
    val = pm.log_loss([1.0], [1])
    assert val == pytest.approx(-np.log(1 - 1e-6), rel=1e-3)
    assert val > 1e-7
    val0 = pm.log_loss([0.0], [0])
    assert val0 == pytest.approx(-np.log(1 - 1e-6), rel=1e-3)


def test_accuracy_and_tie_rule():
    assert pm.accuracy([0.9, 0.1], [1, 0]) == pytest.approx(1.0)
    assert pm.accuracy([0.9, 0.1], [0, 1]) == pytest.approx(0.0)
    # uniform tie rule: p = 0.5 picks team_1
    assert pm.accuracy([0.5], [1]) == pytest.approx(1.0)
    assert pm.accuracy([0.5], [0]) == pytest.approx(0.0)


def test_score_all_shape():
    out = pm.score_all([0.6, 0.4], [1, 0])
    assert out["n"] == 2
    assert out["brier"] == pytest.approx(0.16)
