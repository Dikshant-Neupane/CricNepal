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

## Dry-run findings (2026-10-22) — read before the first real S3 ingest

A full rehearsal (synthetic S3 Bolts vs Karnali fixture built from a
real cricsheet file, run against a copy of the project) found and
fixed two defects that would have bitten on the first match day:

1. `--append` crashed against the production parquets: the ingest
   script emitted types the old pipeline's files do not use
   (match_date as string vs stored date objects, string timestamps,
   all-null columns with degenerate dtypes). The script now aligns
   fresh rows to the existing schema before merging
   (`align_to_existing`), and preview output uses production types too.
2. `player_innings.parquet` and `phase_summary.parquet` were built by
   the original (pre-repo) pipeline and nothing updated them — they
   would have silently stayed at S1/S2 while the dashboard kept
   reading them. `--append` now derives rows for each new match; the
   derivation was verified to reproduce all 1,917 + 378 production
   rows exactly before being trusted.

Also verified in the rehearsal: re-running `--append` is a no-op,
`ball_sequence` continues without collisions, every S3 delivery name
joins the player registry, and `refresh_all.py` completes 20/20 with
an S3 match present. Regression tests:
`tests/test_ingest_cricsheet_append.py`.

## Season mapping

Match-date year → season: 2024 → S1, 2025 → S2, 2026 → S3.
S3 matches will flow into every existing S1/S2 analysis automatically.

## Pre-season state

- `data/player_rosters/npl_player_rosters_20260521.csv` now carries 17
  `Season 3` rows for the confirmed Janakpur Bolts squad
  (5 retained, 8 auction, 4 overseas; Harmeet Singh (c)).
- All 8 squads loaded 2026-10-22: 133 `Season 3` rows total
  (Biratnagar 18, Chitwan 16, Karnali 16, Kathmandu 17, Lumbini 16,
  Pokhara 17, Sudurpaschim 16). Researched from Wikipedia's 2026 NPL
  squad table cross-checked vs Cricfacts/auction trackers/news.
  Returning players use the file's existing name forms (initials-style,
  e.g. `S Lamichhane`, `Gulsan Jha`) so cross-season joins hold.
  NOT loaded (single-source/unconfirmed, watch for announcements):
  Asif Ali + Usama Mir (Chitwan), Haider Ali (Sudurpaschim),
  Shamim Hossain (Lumbini), Mohammad Rubel + Mohammad Saifuddin
  (Pokhara). Judgment calls flagged to Dikshant: `Pratik Shrestha`
  (Biratnagar) and `Sahil Patel` (Kathmandu) loaded under full names —
  the file's `P Shrestha` (Kathmandu S1/S2) and `S Patel` (Biratnagar
  S2) could not be confirmed as the same people.
  RESOLVED 2026-10-22 (see docs/DATA_QUALITY_REPORT.md): both
  confirmed identical via match reports/squad lists/profiles, as were
  `S Karki` = Santosh Karki and the probable merges `K Mahato`,
  `TR Das`, `B Yadav`, `A Yadav`. All S3 rows now use dataset forms;
  canonical identities live in
  data/player_rosters/player_identity_registry.csv (built by
  scripts/build_player_registry.py).
- Bolts open the season Oct 27 vs Karnali Yaks (Match 3).
