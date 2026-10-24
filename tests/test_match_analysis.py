"""Match Predictions — the per-match analysis picker.

Pins: every fixture (all 32) is listed; league matches carry all four
locked series oriented to the fixture's Team 1, expected XIs resolved
to names, and drivers; playoff fixtures carry no probabilities yet;
the page renders with the picker under AppTest.
"""
from pathlib import Path


def test_match_analysis_covers_all_fixtures():
    from src.dashboard.page_modules.match_predictions import (
        load_match_analysis)

    items = load_match_analysis()
    assert len(items) == 32
    league = [m for m in items if m["champion"] is not None]
    playoffs = [m for m in items if m["champion"] is None]
    assert len(league) == 28 and len(playoffs) == 4
    assert all(m["team_1_name"] is None for m in playoffs)


def test_match_analysis_match3_values():
    from src.dashboard.page_modules.match_predictions import (
        load_match_analysis)

    items = load_match_analysis()
    m3 = next(m for m in items if m["match_number"] == 3)
    assert m3["team_1_name"] == "Janakpur Bolts"
    assert m3["team_2_name"] == "Karnali Yaks"
    assert abs(m3["champion"] - 0.5003) < 0.001  # locked pre-season line
    assert m3["simulator"] is not None and m3["coach"] is not None
    assert m3["lock_stage"] == "P1_preseason_expected_xi"
    xi_names = [n for n, _ in m3["xi_1"]]
    assert "Moeen Ali" in xi_names and "Harmeet Singh" in xi_names
    assert "elo_diff" in m3["drivers"]


def test_match_predictions_page_renders_with_picker():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(Path(__file__).parent.parent / "app.py"),
                           default_timeout=180)
    at.session_state["active_page"] = "match_predictions"
    at.run()
    assert not at.exception
    text = "\n".join(m.value for m in at.markdown)
    assert "Match Analysis" in text
    assert len(at.selectbox) >= 1
