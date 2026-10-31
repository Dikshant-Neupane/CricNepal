"""Plan task 5.4 (criteria V1, V5; DISPLAY variant only): the Match
Predictions analysis surfaces the challenger probability WITH its
trained_on disclosure read from the artefact
(data/predictions/model_v1.json) -- never hardcoded, and the
artefact itself is not changed by this task.
"""
import json
from pathlib import Path

import pandas as pd
import pytest

from src.dashboard.page_modules.match_predictions import (
    challenger_disclosure, load_match_analysis)

ROOT = Path(__file__).resolve().parent.parent


def test_disclosure_reads_trained_on_from_artefact(tmp_path):
    pred = tmp_path / "data" / "predictions"
    pred.mkdir(parents=True)
    (pred / "model_v1.json").write_text(json.dumps(
        {"trained_on": "SYNTHETIC WINDOW (3 matches)"}))
    text = challenger_disclosure(tmp_path)
    assert text is not None
    assert "SYNTHETIC WINDOW (3 matches)" in text
    assert "shadow" in text.lower()


def test_disclosure_missing_artefact_returns_none(tmp_path):
    assert challenger_disclosure(tmp_path) is None


def test_real_analysis_carries_oriented_challenger():
    items = {m["match_id"]: m for m in load_match_analysis(ROOT)}
    up = pd.read_csv(ROOT / "data/predictions/upcoming_predictions.csv")
    checked = 0
    for r in up.itertuples():
        item = items[r.match_id]
        assert "challenger" in item
        if item["team_1_name"] == r.team_1_name:
            assert item["challenger"] == pytest.approx(
                float(r.p_logistic_challenger))
        else:
            assert item["challenger"] == pytest.approx(
                1.0 - float(r.p_logistic_challenger))
        checked += 1
    assert checked == 28


def test_real_disclosure_matches_artefact():
    text = challenger_disclosure(ROOT)
    artefact = json.loads(
        (ROOT / "data/predictions/model_v1.json").read_text())
    assert artefact["trained_on"] in text
