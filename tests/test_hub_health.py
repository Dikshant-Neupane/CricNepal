"""Plan 7.1 + 7.3 — Data & Model Health on the Season 3 Hub (B2, B3, D4).

The health section is a Hub section (the showcase nav is frozen, so
no new page). Its loader is a pure function; the B3 behaviour cases —
missing lock, stale prediction status, a conflicts-register entry —
must render visibly rather than silently.
"""
import json
import shutil
from pathlib import Path

import pandas as pd

import src.dashboard.page_modules.season3_hub as hub


def _write_status(root: Path, data_as_of: str) -> None:
    p = root / "data" / "predictions"
    p.mkdir(parents=True, exist_ok=True)
    (p / "predictions_status.json").write_text(json.dumps({
        "data_as_of": data_as_of,
        "generated_at": "2026-10-29T00:00:00+00:00",
    }))


def _write_normalized_with_match(root: Path, match_date: str) -> None:
    p = root / "data" / "normalized"
    p.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{
        "match_id": "s3_2026_01", "season": "S3",
        "match_date": match_date, "winner_name": "Lumbini Lions",
    }]).to_parquet(p / "matches_normalized.parquet", index=False)


def test_load_health_surfaces_stale_status_and_conflicts(tmp_path) -> None:
    _write_status(tmp_path, "2025-12-13")
    _write_normalized_with_match(tmp_path, "2026-10-26")
    reg = tmp_path / "data" / "conflicts_register.csv"
    reg.parent.mkdir(parents=True, exist_ok=True)
    reg.write_text(
        "conflict_id,detected,type,scope,source_a,value_a,source_b,value_b,status,resolution,notes\n"
        "CONF-001,2026-10-29,team_identity_split,scope,a,Gorkhas,b,Gurkhas,open,none,note\n")

    health = hub.load_health(tmp_path)
    # Status predates a played match in the canonical data -> stale.
    assert health["predictions_status"]["available"] is True
    assert health["predictions_status"]["data_as_of"] == "2025-12-13"
    assert health["predictions_status"]["stale"] is True
    # The conflict is carried through verbatim, not summarised away.
    assert health["conflicts"]["available"] is True
    assert health["conflicts"]["rows"][0]["conflict_id"] == "CONF-001"
    assert health["conflicts"]["rows"][0]["status"] == "open"


def test_load_health_degrades_on_empty_root(tmp_path) -> None:
    health = hub.load_health(tmp_path)
    assert health["predictions_status"]["available"] is False
    assert health["conflicts"]["available"] is False
    assert health["models"]["available"] is False
    assert all(not d["exists"] for d in health["datasets"])


def test_load_health_reads_model_labels_with_ci() -> None:
    health = hub.load_health(Path(hub.ROOT))
    models = health["models"]
    assert models["available"] is True
    assert abs(models["champion_log_loss"] - 0.689088) < 1e-4
    assert abs(models["elo_log_loss"] - 0.688848) < 1e-4
    assert models["champion_vs_elo_ci_includes_zero"] is True
    assert "no demonstrated improvement" in models["label"]
    # Plan 5.5: the in-play paired comparison is surfaced with its CI.
    ip = models["inplay_vs_baseline"]
    assert ip["includes_zero"] is True
    assert ip["ci_low"] < 0 < ip["ci_high"]
    assert "not established" in ip["verdict"]


# ---- B3 render behaviour (AppTest, hub page only) ----

def _copy_hub_root(tmp_path: Path) -> Path:
    root = Path(hub.ROOT)
    for rel in hub.HUB_DATA_FILES:
        if rel.endswith("matches_normalized.parquet"):
            continue
        dest = tmp_path / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(root / rel, dest)
    return tmp_path


def _run_hub(tmp_path: Path, root: Path):
    from streamlit.testing.v1 import AppTest

    repo = Path(__file__).parent.parent
    runner = tmp_path / "run_hub.py"
    runner.write_text(
        "import sys\n"
        f"sys.path.insert(0, {str(repo)!r})\n"
        "from pathlib import Path\n"
        "import src.dashboard.page_modules.season3_hub as hub\n"
        f"hub.ROOT = Path({str(root)!r})\n"
        "hub.render_season3_hub()\n"
    )
    # AppTest executes in this process: the runner's ROOT rebind would
    # leak into every later test, so restore it (and the loader cache)
    # as soon as the run completes.
    old_root = hub.ROOT
    try:
        at = AppTest.from_file(str(runner), default_timeout=120)
        at.run()
    finally:
        hub.ROOT = old_root
        hub._load_season3_cached.clear()
    assert not at.exception
    return at


def test_b3_missing_lock_renders_as_dash_not_silence(tmp_path) -> None:
    root = _copy_hub_root(tmp_path)
    frozen_path = root / "data" / "predictions" / "frozen_log.csv"
    frozen = pd.read_csv(frozen_path)
    # Remove every lock for the opener: the next-match metrics must
    # show the gap ("—"), not a number or a crash.
    frozen = frozen[frozen.match_id != "s3_2026_01"]
    frozen.to_csv(frozen_path, index=False)

    at = _run_hub(tmp_path, root)
    metric_values = [m.value for m in at.metric]
    assert "—" in metric_values


def test_b3_conflict_entry_renders_a_visible_warning(tmp_path) -> None:
    root = _copy_hub_root(tmp_path)
    reg = root / "data" / "conflicts_register.csv"
    reg.parent.mkdir(parents=True, exist_ok=True)
    reg.write_text(
        "conflict_id,detected,type,scope,source_a,value_a,source_b,value_b,status,resolution,notes\n"
        "CONF-001,2026-10-29,team_identity_split,scope,a,Gorkhas,b,Gurkhas,open,none,note\n")

    at = _run_hub(tmp_path, root)
    warnings = [w.value for w in at.warning]
    assert any("conflict" in w.lower() for w in warnings)
    markdown = "\n".join(m.value for m in at.markdown)
    assert "Data & model health" in markdown


def test_b3_missing_conflicts_register_renders_a_visible_warning(tmp_path) -> None:
    root = _copy_hub_root(tmp_path)
    at = _run_hub(tmp_path, root)
    warnings = [w.value for w in at.warning]
    assert any("conflicts register" in w.lower() for w in warnings)
