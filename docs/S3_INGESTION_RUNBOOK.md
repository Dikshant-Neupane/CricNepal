# Season 3 ingestion runbook (NPL 2026, Oct 26 – Nov 21)

## After each match day

Cricsheet publishes NPL ball-by-ball JSONs with a delay (usually days).
Grab the latest bundle and ingest:

```bash
cd /tmp && rm -rf cricsheet && mkdir cricsheet && cd cricsheet
curl -sL -o npl_json.zip https://cricsheet.org/downloads/npl_json.zip
unzip -o -q npl_json.zip -d npl_json

cd ~/workspace/cricnepal   # or wherever the repo lives
.venv/bin/python scripts/ingest_cricsheet.py /tmp/cricsheet/npl_json --append
```

`--append` merges only new `match_id`s into
`data/final/parquet/{matches,ball_by_ball}.parquet` and continues the
global `ball_sequence` counter. Without `--append` it writes preview
parquets and touches nothing.

## Rebuild derived data

```bash
.venv/bin/python -m src.preprocessing.normalize_data
.venv/bin/python refresh_all.py
```

## What was validated (2026-10-18)

`scripts/ingest_cricsheet.py` was round-trip tested against the existing
S1/S2 data: converting the 64 cricsheet NPL JSONs reproduces all 14,937
deliveries byte-identical on every field. The only differences are strict
improvements the old pipeline had dropped:

- `fielder_name` populated (was all-null in old deliveries)
- `player_of_match` populated (was all-null in old matches)
- `innings_1_*` / `innings_2_*` summaries populated (were all-null)

Conventions matched exactly: `match_id = espn_<cricsheet_id>`,
`source_system = Cricsheet`, 0-indexed overs, per-match-cumulative
`ball_sequence` (continued globally on append), phase
Powerplay(0-5)/Middle(6-14)/Death(15-19), `is_dot_ball = (runs_total==0)`,
team_1/team_2 alphabetical, `Sudur Paschim Royals → Sudurpaschim Royals`
in the matches table (delivery rows keep raw cricsheet names, as before).

## Season mapping

Match-date year → season: 2024 → S1, 2025 → S2, 2026 → S3.
S3 matches will flow into every existing S1/S2 analysis automatically.

## Pre-season state

- `data/player_rosters/npl_player_rosters_20260521.csv` now carries 17
  `Season 3` rows for the confirmed Janakpur Bolts squad
  (5 retained, 8 auction, 4 overseas; Harmeet Singh (c)).
- Bolts open the season Oct 27 vs Karnali Yaks (Match 3).
