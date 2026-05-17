import pandas as pd

from src.dashboard.services.data_quality import REQUIRED_MATCH_FIELDS, validate_match_records


def _valid_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "season": "S1",
                "competition_name": "NPL Season 1",
                "competition_tier": "A",
                "opposition_strength_bucket": "strong",
                "match_context": "league",
                "result": "W",
                "runs_for": 176,
                "runs_against": 162,
                "overs_faced": 20.0,
                "overs_bowled": 20.0,
            }
        ]
    )


def test_validate_match_records_healthy_payload() -> None:
    report = validate_match_records(_valid_df())

    assert report["status"] == "healthy"
    assert report["error_count"] == 0
    assert report["warning_count"] == 0
    assert report["reliability_score"] == 100


def test_validate_match_records_detects_missing_columns() -> None:
    df = _valid_df().drop(columns=["match_context", "result"])
    report = validate_match_records(df)

    assert report["status"] == "blocked"
    assert report["error_count"] >= 1
    assert "Missing required columns" in report["findings"][0]["message"]


def test_validate_match_records_detects_invalid_values() -> None:
    df = _valid_df().copy()
    df.loc[0, "competition_tier"] = "X"
    df.loc[0, "match_context"] = "friendly"
    df.loc[0, "opposition_strength_bucket"] = "elite"
    df.loc[0, "result"] = "T"

    report = validate_match_records(df)

    messages = {item["message"] for item in report["findings"]}
    assert "Invalid competition_tier values" in messages
    assert "Invalid match_context values" in messages
    assert "Invalid opposition_strength_bucket values" in messages
    assert "Invalid result values" in messages


def test_validate_match_records_flags_low_completeness() -> None:
    df = _valid_df()
    for field in REQUIRED_MATCH_FIELDS:
        df.loc[0, field] = None

    report = validate_match_records(df)

    assert report["warning_count"] >= 1
    assert any(item["message"] == "Required fields below 95% completeness" for item in report["findings"])
