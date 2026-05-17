import pandas as pd

from src.dashboard.services import data_source


def test_load_match_records_uses_database_when_available(monkeypatch) -> None:
    db_df = pd.DataFrame(
        [
            {
                "season": "S2",
                "competition_name": "NPL Season 2",
                "competition_tier": "A",
                "opposition_strength_bucket": "balanced",
                "match_context": "league",
                "result": "W",
                "runs_for": 170.0,
                "runs_against": 160.0,
                "overs_faced": 20.0,
                "overs_bowled": 20.0,
            }
        ]
    )

    monkeypatch.setattr(data_source, "_load_from_database", lambda: db_df)

    out_df, source = data_source.load_match_records()
    assert source == "database"
    assert not out_df.empty
    assert out_df.iloc[0]["competition_name"] == "NPL Season 2"


def test_load_match_records_falls_back_to_demo_on_db_error(monkeypatch) -> None:
    monkeypatch.setattr(data_source, "_load_from_database", lambda: (_ for _ in ()).throw(RuntimeError("db down")))

    out_df, source = data_source.load_match_records()
    assert source == "demo"
    assert not out_df.empty
