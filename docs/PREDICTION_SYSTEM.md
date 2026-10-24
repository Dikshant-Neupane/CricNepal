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
champion/challenger rule -- a reused backtest is not proof. An audit of
that advantage (2026-10-24, `scripts/audit_simulator.py`) found the
paired-bootstrap 95% CI for simulator-minus-champion log-loss includes
zero: **the simulator advantage is not established** -- see the
bootstrap section below.

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
  schedule, teams TBA. Start times are now recorded under CAN's revised
  timings of 2026-10-20 — see the fixture-time correction record below.
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

## The three systems (review fix, 2026-10-24)

Pre-match, toss-adjusted and in-play forecasts are different prediction
tasks. They are enforced as separate systems (input contracts in
`src/prediction/engine.py: STAGE_INPUTS`), scored separately, and never
pooled into one number.

| System | Allowed inputs | Lock time | Evaluation | Current status |
|---|---|---|---|---|
| 1. Pre-match (P1, incl. `P1_preseason_expected_xi`) | Team ratings (Elo), expected/confirmed XI strength from player priors, form (EWMA NRR), rest days. **Toss fields are forbidden** — the engine refuses any toss input at this stage. | P1_preseason: before the tournament (expected XIs). P1: after XI announcement, before the toss. | Frozen log, per stage, vs Elo and chase-heuristic baselines (log-loss / Brier / accuracy). | 28 pre-season P1s locked. S2 backtest: champion log-loss 0.6891 vs Elo 0.6888; bootstrap CI for the difference includes zero — no demonstrated edge (below). |
| 2. Toss-adjusted (P2) | Everything in P1 **plus** toss winner + decision (both required — the engine refuses P2 without them). | After the toss, before the first ball. | Frozen log, stage `P2` only, reported separately from every P1 stage. | No P2 rows locked yet; locks on matchdays via `scripts/predict_fixtures.py --toss-csv`. Kirtipur chase premium in the adjustment: 33/63 (52.4%), logit shift 0.095. |
| 3. In-play win probability | Current match state only: balls remaining, runs scored/required, wickets, current/required run rate (per innings). No pre-match inputs. | Continuous during the match (not locked). | **Separate, delivery-level**: `scripts/evaluate_inplay_wp.py` trains on S1 only and scores S2 deliveries -> `data/predictions/inplay_wp_evaluation.json`. NOT comparable to P1/P2 metrics. | Out-of-sample (S1->S2): log-loss 0.543, Brier 0.187, delivery-level accuracy 69.7% over 7,439 deliveries (innings 1: log-loss 0.662; innings 2: 0.411). Production model in `refresh_all` still trains on all data — the evaluation harness changes nothing about it. |

## Fixture-time correction record (R1)

- **Before:** `start_time_local` was blank for all 32 fixtures. Sources
  conflicted: the revised CAN graphic implied 12:30/17:00 while
  cricketer.io listed 12:15/16:15, so no time was recorded rather than
  guess.
- **Correction (2026-10-24):** CAN revised the timings on 2026-10-20
  when Hawk-Eye DRS was introduced — the evening start moved from
  16:30 to 17:00. The revised rule, reported from CAN's press statement
  by nepalontheweb.com and english.khabarhub.com (both opened and read
  2026-10-24), corroborated by Radio Nepal, Khabarhub, myRepublica and
  Nepal News reporting of the same statement: **double-header days —
  first match 12:30, second 17:00; single-match days — 17:00.**
  Playoff days (Nov 17/18/19/21) are single-match days -> 17:00.
- **After:** all 32 fixtures carry a verified slot time under that rule,
  with per-row `start_time_source` and `start_time_accessed`
  (2026-10-24) and `start_time_verification` fields. Within a
  double-header day, match order is the CAN fixture-graphic order
  (as already used for pairings). No row remains unresolved. Fixture
  times do not enter any locked prediction and the frozen log was not
  modified by this change.

## Bootstrap uncertainty (R3/R4, 2026-10-24)

Paired bootstrap over matches (10,000 resamples, fixed seed 42) of
per-match log-loss differences on the Season 2 backtest
(`scripts/audit_simulator.py` -> `data/predictions/simulator_audit.json`;
the champion-Elo figures are also in `backtest_metrics.json`):

| Difference (log-loss) | Mean | 95% CI | P(first is better) | Reading |
|---|---|---|---|---|
| Simulator − champion | −0.034 | [−0.104, +0.043] | 0.82 | **Includes zero — advantage not established** (pre-committed verdict rule). |
| Simulator − Elo | −0.034 | [−0.115, +0.052] | 0.79 | Includes zero. |
| Champion − Elo | +0.000 | [−0.023, +0.023] | 0.49 | Dead even. The headline model has no measurable edge over Elo alone on S2. |

Accuracy differences tell the same story with wider intervals
(simulator − champion accuracy +0.219, CI [0.000, 0.438]). The audit
also verified the three backtests are scored on the identical 32 match
IDs, and its leakage checklist passes the S1-only distribution fit and
the as-of priors, while flagging: XIs in the simulator backtest are the
actual XIs that played (post-hoc), the simulator's constants have no
pre-registered record (tuning-against-S2 cannot be ruled out from the
artefacts), and 2,000-sim Monte Carlo noise (~0.011 per match) is not
inside the bootstrap CIs. **Promotion rule unchanged:** the simulator
stays shadow until it beats the champion on the S3 frozen log.

## Limits of a 32-match season

- **Accuracy noise:** with n=32 matches, the standard error of an
  accuracy estimate is about sqrt(0.25/32) ≈ **±9 percentage points**.
  A season finishing at 62% and one at 50% are statistically
  indistinguishable at this sample size.
- **Calibration cannot be certified in one season:** a calibration bin
  holding ~6 matches has a binomial standard error above ±20 points.
  This is why calibration is reported only in coarse bins and why no
  calibration claim will be made from Season 3 alone; several seasons
  of frozen predictions must be pooled before calibration can be
  assessed honestly.
- **Log-loss differences of the size seen here (~0.03) are within
  noise** at n=32, as the bootstrap CIs above show.
- Therefore the S3 frozen log is **evidence, not proof**: it is a
  genuine prospective test (predictions locked before matches, never
  rewritten), which makes it far stronger than another backtest — but
  a single season can at most shift confidence, not settle which model
  is best. Model decisions (promotion, refits at the match-10/20
  checkpoints) follow the pre-committed rules regardless of how the
  early results feel.
