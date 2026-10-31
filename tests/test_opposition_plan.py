"""Plan task 6.3 (criteria S2, S3, S4): the opposition plan
generator takes the opponent as an input. Two different opponents
must produce materially different plans; no plan may contain
line/length/delivery-style claims or a "weakness" label; entries on
Limited evidence must carry no targeting action.
"""
import json
import re
from pathlib import Path

import pandas as pd
import pytest

from src.prediction.opposition_plan import (
    evidence_label, generate_opposition_plan)

ROOT = Path(__file__).resolve().parent.parent
PRED = ROOT / "data" / "predictions"

BANNED = [r"\bline\b", r"\blength\b", r"yorker", r"bouncer",
          r"weakness", r"weak against", r"struggles against"]


def _scan(plan):
    text = json.dumps(plan).lower()
    for pat in BANNED:
        assert not re.search(pat, text), f"banned content: {pat}"


def test_evidence_labels():
    assert evidence_label(10) == "Limited"
    assert evidence_label(30) == "Moderate"
    assert evidence_label(120) == "Moderate"
    assert evidence_label(121) == "Strong"


def test_two_opponents_produce_materially_different_plans():
    priors = pd.read_csv(PRED / "player_priors.csv")
    a = generate_opposition_plan("Biratnagar Kings", priors)
    b = generate_opposition_plan("Lumbini Lions", priors)
    assert json.dumps(a, sort_keys=True) != json.dumps(b, sort_keys=True)
    acts_a = [e["action"] for e in a["bowling_plan"] + a["batting_plan"]]
    acts_b = [e["action"] for e in b["bowling_plan"] + b["batting_plan"]]
    assert acts_a != acts_b
    obs_a = [e["observation"] for e in a["bowling_plan"]]
    obs_b = [e["observation"] for e in b["bowling_plan"]]
    assert obs_a != obs_b
    _scan(a)
    _scan(b)


def test_structure_and_evidence_fields():
    priors = pd.read_csv(PRED / "player_priors.csv")
    plan = generate_opposition_plan("Karnali Yaks", priors)
    assert plan["opponent"] == "Karnali Yaks"
    assert len(plan["janakpur_expected_xi"]) == 11
    for section in ("bowling_plan", "batting_plan"):
        assert [e["phase"] for e in plan[section]] == [
            "powerplay", "middle", "death"]
    for e in plan["bowling_plan"] + plan["batting_plan"]:
        ev = e["evidence"]
        assert set(ev) == {"n_balls", "baseline", "estimate",
                           "interval", "label"}
        assert e["limitation"] and e["action"] and e["alternative"]
        if ev["label"] == "Limited":
            assert "No phase-specific change" in e["action"]
    _scan(plan)


def test_unknown_opponent_rejected():
    priors = pd.read_csv(PRED / "player_priors.csv")
    with pytest.raises(ValueError, match="no priors rows"):
        generate_opposition_plan("No Such Team", priors)


def test_team_level_with_approach_and_h2h():
    priors = pd.read_csv(PRED / "player_priors.csv")
    approach = pd.read_csv(ROOT / "data/approach/team_approach_profiles.csv")
    h2h = pd.read_csv(ROOT / "data/approach/head_to_head.csv")
    plan = generate_opposition_plan("Chitwan Rhinos", priors,
                                    approach=approach, head_to_head=h2h)
    assert len(plan["team_level"]) == 2
    _scan(plan)
