# CricNepal Pre-Match Prediction System

Predicts every NPL Season 3 fixture before it is played, and updates after
every match. Design follows the 2026-10-24 research report
(`~/workspace/research_notes/t20-prematch-prediction-system-20261024-0512/report.md`):
shrinkage-first, no gradient boosting, <=6 difference features, locked
P1/P2 predictions, frozen log, Elo + player updates after each match,
coefficients frozen between checkpoints.

## Architecture

| Piece | Where |
|---|---|
| S3 fixtures (32) | `data/fixtures/s3_fixtures.csv` via `scripts/build_s3_fixtures.py` |
| Player master (133) | `data/predictions/player_master.csv` via `scripts/build_player_master.py` |
| Cross-league history + priors | `data/predictions/player_history.csv`, `player_priors.csv` via `scripts/build_player_priors.py` |
| Canonical Elo (the ONLY Elo for prediction) | `src/prediction/elo.py`; outputs `data/predictions/elo_history.csv`, `team_ratings_current.csv`, `elo_tuning.csv` |
| Model + champion blend | `src/prediction/model.py`; artifact `data/predictions/model_v1.json` |
| Prediction engine + frozen log | `src/prediction/engine.py`, `scripts/predict_fixtures.py`, `data/predictions/frozen_log.csv` |
| Scoring | `scripts/score_predictions.py` -> `data/predictions/scorecard.csv` |
| Monte Carlo simulator (SHADOW) | `src/prediction/simulator.py`, `scripts/backtest_simulator.py` |
| In-season refresh | `scripts/refresh_predictions.py` (step in `refresh_all.py`, after Elo) |
| Dashboard | `src/dashboard/page_modules/match_predictions.py` |

`scripts/compute_team_elo.py` is now a wrapper over the canonical engine
(K=20, 40% between-season regression, margin-of-victory capped at 1.5x).
`opposition_strength_analysis.py` keeps its own history for the SOS/WAE
dashboard outputs; do not use it for prediction.

## The model (v1)

Headline probability = **champion blend**:
`p = 0.5 * p_elo + 0.5 * p_xi`, where `p_xi = logistic(2.0 * (xi_batting_diff
+ xi_bowling_diff))` with the scale FIXED a priori, then clipped to
[0.05, 0.95]. XI strength = mean batting/bowling index of the expected XI
from the shrunk player priors.

A regularised logistic regression on the five P1 difference features
(elo_diff, xi_batting_diff, xi_bowling_diff, form_nrr_diff, rest_diff)
exists as **challenger** (`p_logistic_challenger`). On the Season 2
walk-forward backtest it lost badly to Elo (log-loss 0.796 vs 0.689) --
S1-fitted signs do not survive auction churn -- so it does not headline.
Backtest (S2, n=32): champion blend accuracy 46.9%, log-loss 0.6891,
Brier 0.2480; higher-Elo baseline 43.8% / 0.6888 / 0.2480; coin flip
0.6931 log-loss; chase heuristic 0.7026. **Read that honestly: on S2 the
system demonstrated no edge over Elo alone.** The S3 frozen log is the
decisive test.

The Monte Carlo simulator beat the blend on the same backtest (accuracy
68.8%, log-loss 0.655, Brier 0.231, distributions fitted on S1 only,
2,000 sims/match). It nevertheless stays in **shadow mode**: it may only
be promoted if it beats the champion on the S3 frozen log, per the
champion/challenger rule -- a reused backtest is not proof.

## Player priors

Per player, last ~3 years of T20 history from cricsheet across NPL, T20I,
IPL, PSL, BBL, BPL, CPL, LPL, ILT20, SA20 and MLC, joined on the cricsheet
registry ID, decay-weighted (18-month half-life). Cross-league translation
acts on the deviation from the source league's mean (per-league factor
0.80-1.00, documented assumption). Priors shrink to the NPL mean with
k=150 balls faced / k=120 balls bowled. Groups: `npl_experienced` (91),
`external_pro` (14, 1.5x uncertainty), `debutant` (28, league-mean prior,
1.5x uncertainty). Priors are in `player_priors.csv` with phase splits.

## Matchday workflow

1. **Pre-season (done 2026-10-24):** P1 locked for all 28 league fixtures
   at stage `P1_preseason_expected_xi` (expected XIs from priors; labelled
   as such, they are the weakest predictions of the season).
2. **Matchday, after XI announcement, before toss:** capture the actual
   XIs (they arrive with the scorecard feed / broadcast), regenerate, and
   lock stage `P1`. (The engine's XI input for P1 is the expected-XI
   selector; when actual XIs are captured into
   `data/final/parquet/match_lineups.parquet` for upcoming fixtures, they
   supersede the selector -- that capture step is manual until a live
   XI source is wired.)
3. **After the toss, before first ball:** run
   `python scripts/predict_fixtures.py --toss-csv <file>` with
   match_id,toss_winner_name,toss_decision to lock stage `P2`. The P2
   adjustment is the Kirtipur chase premium estimated from S1+S2
   (chasing teams won 33/63 decided matches, 52.4%; logit shift 0.095) --
   small, because Kirtipur is not a dew-heavy outlier in our data.
4. **After the match:** the in-season update (cricsheet ingest -> normalize
   -> refresh_all) updates Elo and player priors, regenerates unlocked
   probabilities for remaining fixtures, and re-scores the frozen log.
   Locked rows are never rewritten; `lock_predictions` refuses duplicates
   of (match_id, stage).

## Checkpoint rule (coefficients)

Logistic coefficients, blend weights and calibration are FROZEN during
the season except at two checkpoints: after S3 matches 10 and 20. At a
checkpoint a refit (pooled data, previous fit as prior) may be proposed;
it is promoted to champion only if it beats the frozen champion on
frozen-log log-loss over the matches since the previous checkpoint.
Otherwise the frozen model continues. Any promotion increments
MODEL_VERSION and starts a new frozen-log segment.

## Data sources and known gaps

- Fixtures: league stage from the CAN fixture graphic via
  nepinsights.com, cross-checked with ipl.com (pairings/dates agree);
  playoff dates/stages from nepalontheweb.com's report of CAN's revised
  schedule, teams TBA. Start times are NOT recorded: sources conflict
  (revised CAN timings vs cricketer.io). They must come from CAN's
  official announcement before being added.
- Player details: roster + identity registry + enriched profiles (joined
  via registry surface forms). Registry IDs resolved for 108/133 players
  (101 exact name matches, 7 constrained initials-surname-unique matches
  flagged in `registry_id_match_type`); the unresolved 25 are mostly uncapped domestic players with
  no cricsheet appearance yet -- they resolve when they first play.
  Nationality known for 93/133, DOB for 60/133. Unsourced = null + flagged
  in `missing_fields`, never guessed.
- XI capture: `scripts/ingest_cricsheet.py` now writes
  `data/final/parquet/match_lineups.parquet` (backfilled: 1,408 rows,
  64 matches x 22, all with registry IDs).
- Cricsheet zips are read from `CRICSHEET_ZIP_DIR` (default
  `~/workspace/.scratch/predbuild`); they are not stored in the repo.

## Corrections log

- 2026-10-24: one pre-season locked row (s3_2026_05) was generated while
  the fixtures file carried the source spelling "Kathmandu Gurkhas"
  instead of the canonical "Kathmandu Gorkhas", so Kathmandu's rating
  defaulted to 1500 in that row. The fixtures file was corrected and that
  single row's team name and probabilities were regenerated (champion
  blend 0.4718 with the correct 1515.7 rating (was 0.4889 with the default 1500)). No other locked row was
  touched; the season had not started and no prediction had been
  published or scored. Append-only applies from here on.
