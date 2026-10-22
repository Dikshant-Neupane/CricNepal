# CricNepal Data Quality Report

Generated 2026-10-22 after a full audit, cross-validation of previous
(S1/S2) vs current (S3) data, and a player-identity resolution program.
Companion artifacts:

- `data/player_rosters/player_identity_registry.csv` — one row per
  unique player (228), with canonical name, every surface form,
  identity status and the evidence behind it. Built by
  `scripts/build_player_registry.py`; re-run it after any roster or
  source-data change.
- `data/player_rosters/npl_player_rosters_canonical.csv` — the roster
  plus `player_key`, `canonical_name`, `identity_status` columns.
  **This is the analysis-ready roster. Join and group on `player_key`,
  never on raw player names.**

## 1. Validation verdict

25 cross-checks were run across roster, deliveries (14,937),
matches (64), player_innings, phase_summary and the normalized
parquets. Previous data is internally consistent and reconciles
exactly (see §3). The material defects found were all in *identity
resolution* for Season 3 rows (§2) and are fixed.

## 2. Player identity resolution

Surface forms in the datasets are ESPN-style (`S Lamichhane`,
`P Shrestha`); squad announcements and news use full names. Any S3
row loaded under a full name silently splits that player's history.

**Method (two-signal rule):** an alias is marked `confirmed` only
with at least two independent signals — e.g. team continuity in the
data plus a squad list, match report, the official CAN 2026 auction
pool, or a player profile. Weaker evidence is `probable`; anything
else is left unmerged.

**Outcome:** 228 unique players from 229 dataset surface forms;
114 confirmed aliases, 90 single-form players, 1 probable, 23
initials forms whose full names appear in no verifiable source
(mostly fringe players with tiny samples; `JJ Smit` plays under his
initials professionally). The registry carries the evidence string
for every alias.

Headline resolutions (all `confirmed`):

| Dataset form | Canonical player | Decisive evidence |
|---|---|---|
| P Shrestha | Pratik Shrestha | S1 report: top-scored 39 for Kathmandu; S2 Kathmandu squad lists; Biratnagar bought him at the 2026 auction |
| S Patel | Sahil Patel | TOI profile (WK, b. 2007, Biratnagar Kings); S2 Biratnagar scorecards (19 off 24 vs Karnali) |
| S Karki | Santosh Karki | S1 reports, Dec 2 2024: 28* top-scored for Chitwan vs Kathmandu; Bolts' 2026 auction buy |
| K Mahato | Kishore Mahato | Cricinfo/Wikipedia (RAMF, Janakpur 2024–); 4 wickets in the S1 final; Lumbini's NPR 10 lakh S3 buy |
| TR Das | Trit Raj Das | Pokhara S2 lists + 29 off 28 vs Janakpur; Bolts' S3 buy (one preview spells him Tirtha Raj Das) |
| B Yadav | Bibek Kumar Yadav | Lumbini S1 data + S2 squad list; Chitwan S3 signing |
| A Yadav | Arniko Prasad Yadav | S1 reports: Arniko Yadav took 2 wickets for Janakpur, Dec 2024 |

Confirmed **non**-merges (look-alikes that are different people):
`SM Dhakal` (Karnali S1) is not Mousom Dhakal (Chitwan S3);
`Sunny Patel` (Kathmandu S2) is not Sahil Patel; `Dipak Bohara`
(Sudurpaschim) is not `Deepak Bohara` (Chitwan); `N Bhatta`
(Naren Bhatta) is not `N Saud` (Naren Saud).

## 3. Dataset conventions (verified, do not "fix")

These look like errors until checked against the data. They hold
uniformly across both seasons:

- **Overs are decimal** `round(balls / 6, 1)` everywhere (roster
  `overs_bowled`, scorecard backfill). Not cricket notation.
- **Bowler wickets include run outs** that occur during their overs:
  roster `wickets_taken` equals the count of `is_wicket` deliveries
  per bowler, run outs included (0 diffs over 258 player-seasons).
- **Roster `total_matches` counts XI appearances.** 20 players appear
  in deliveries in 1–2 extra matches — substitute-fielding cameos.
  Roster never exceeds deliveries.
- **Team names:** `data/final` parquets keep raw source spellings
  (`Kathmandu Gurkhas`, `Sudur Paschim Royals`); `data/normalized`
  is canonical (8 teams). Dashboard and analytics read normalized.
- **`ball_sequence` is global** (1..14,937 across the dataset),
  continued on append — by design, not per-match.
- **Results integrity:** winner, win margin and toss winner match
  the ball-by-ball scores for all 64 matches; the one winner-less
  match is the tie (super overs exist as innings 3/4).
- **Roster runs reconcile exactly** with delivery `runs_off_bat`
  for every S1/S2 player-season; player_innings and phase_summary
  rebuild exactly from deliveries; backfilled innings fields are
  exact. One approximation to know: backfilled `innings_X_overs`
  counts *deliveries* (incl. wides/no-balls) / 6, so it can exceed
  legal overs (e.g. 21.2). It is pinned by the backfill tests; treat
  it as delivery volume, not legal overs.

## 4. Defects and notes in supporting data

- **Enriched profiles DOB conflict:** `K Mahato` profile DOB
  2001-10-30 conflicts with Cricinfo/Wikipedia (Kishore Mahato,
  2000-04-02). Unresolved — Cricinfo is the usual authority, but the
  profile value was not overwritten without a primary source.
- Profiles lack DOB for most domestic players (enrichment gap, not
  an error).
- **Role correction from a primary source:** the official CAN 2026
  auction pool lists Salahuddin Khan as an all-rounder; his S3
  roster row was updated from the unconfirmed "Batter".
- **Spelling variants in sources** (dataset form kept; variants in
  the registry evidence): Kishore/Kishor Mahato, Aadity/Aditya
  Mahata, Trit/Tirtha Raj Das, Prashiddha Jaisi/Jaishi,
  Mousom/Mausam Dhakal, Imran Sheikh/Shekh, Abhishesh/Abhisesh
  Gautam.

## 5. Guidance for analysis

1. Group players by `player_key` (canonical roster or registry).
   Grouping by raw name understates every renamed player — 114 of
   228 players have a confirmed full-name identity behind an
   initials form.
2. Read match/delivery data from `data/normalized`, not
   `data/final` (raw team spellings fragment team aggregates).
3. S3 roster rows are squad registrations with zero stats until
   cricsheet ingestion lands (expected from ~Oct 29). At ingest
   time, map incoming cricsheet names through the registry before
   joining — cricsheet uses its own name forms.
4. Treat `innings_X_overs` as deliveries/6 (see §3) in any
   run-rate or workload math.
5. The 13 skipped `test_s3_recruiting` tests need the ridge-model
   deliverables (`s3_predictions_ridge_ranked.csv`,
   `s3_model_comparison.csv`) whose generator scripts were never
   committed. Until they are, the recruiting page's data path is
   only partially covered by tests.
