# CricNepal Pre-Match Prediction System

Predicts every NPL Season 3 fixture before it is played. Ratings,
player priors and regenerated (unlocked) forecasts update after every
match **whose cricsheet data has been published and ingested** —
cricsheet publication lags real time (measured on Season 2: median
8 days, range 0–14; see "Data publication lag" below), so
early-season forecasts may rest on pre-season ratings for the first
several matchdays. The matchday P1_post_XI / P2 locks do not depend
on cricsheet (manual XI/toss capture) and are unaffected by the lag.
Design follows the 2026-10-24 research report
(`~/workspace/research_notes/t20-prematch-prediction-system-20261024-0512/report.md`):
shrinkage-first, no gradient boosting, <=6 difference features, locked
P1/P2 predictions, frozen log, Elo + player updates after each
published-and-ingested match, coefficients frozen between checkpoints.

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
| Matchday capture (XI / toss locks) | `scripts/lock_matchday.py`; formats in `data/matchday/README.md` |
| Temperature calibration (v1.1) | `scripts/fit_temperature.py` -> `data/predictions/model_v1_1.json` |
| Simulator preseason shadow locks | `scripts/simulate_fixtures.py` -> stage `SIM_shadow_preseason` |
| Pre-registration (frozen constants + rules) | `docs/PREREGISTRATION_S3.md` + `data/predictions/preregistration_s3.json` |
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

**Parameter provenance (F1 audit, 2026-10-24).** The Elo constants
(K=20, season regression 0.40) were selected from a grid scored on
this same Season 2 walk-forward — selection on the reported test set.
The bound is measured, not guessed: the grid actually searched
(K 20–32 × regression 0.25–0.40, saved in `elo_tuning.csv`) spans only
0.0050 of log-loss, so S2 figures for Elo-family models are mildly
optimistic **by at most 0.0050** (outer envelope over the wider
default grid: 0.0201). Clean reselection within Season 1 alone picks
K=28, which scores 0.68913 on S2 — within 0.0003 of the shipped
constants, which are kept for Season 3 (Pre-registration Amendment
#3). The regression parameter cannot be selected within one season;
0.40 rests on the research prior (25–40%), not on clean selection.
Full audit: `data/predictions/elo_selection_audit.json`. Standing
rule from here on: parameter selection is nested — earlier seasons
only, never the season being reported.

**Baseline definition audit (F2, 2026-10-24).** `backtest_metrics.json`
used to report a coin-flip "accuracy" of 0.34375. That number was
never a coin measurement: the old code scored p = 0.5 for every match
through the generic accuracy function, whose `p >= 0.5` convention
turns every exact-0.5 prediction into a team_1 pick — so the "coin
accuracy" was exactly the Season 2 team_1 win share (11/32). The coin
baseline is now definitional (`metrics.coin_baseline_metrics`):
log-loss ln 2 ≈ 0.6931, Brier 0.25, **accuracy null** (0.5 in
expectation by symmetry; a computed value would restate the sample's
team_1 share). The same audit made the tie rule explicit and uniform
for every model and baseline (`metrics.TIE_RULE`): an exact p = 0.5
picks team_1 by convention and is scored normally. On the S2 backtest
the convention actually bites only for the chase heuristic (3 exact
0.5 predictions, all scored as team_1 picks, all incorrect); the
champion blend, the logistic challenger, the higher-Elo baseline (no
exactly-equal S2 pre-match ratings) and the simulator have zero exact
ties, and **no reported accuracy changes** under the clarified rule —
every stored accuracy was recomputed from the saved prediction files
and matches.

**As-of invariance (G2 audit, 2026-10-24).** The backtest's temporal
boundaries are regression-tested, not just asserted
(`tests/test_review_response_g.py`): (a) recomputing the Elo history
on data truncated at five points inside Season 2 reproduces every
earlier match's pre-match ratings and expected scores exactly —
later matches cannot move an earlier rating state; (b) the priors
used for the S2 backtest are built as of 2025-11-17 (the S2 start):
for the NPL bundle this is data-verified — an independent scan of the
raw cricsheet files, date-restricted on its own, reproduces the
aggregation's decay-weighted ball totals exactly, with all 32 S2
matches excluded by the cutoff (the shared date filter is also
unit-tested on a synthetic bundle; the production `player_history.csv`
retains no dates, so its cutoff rests on the same code path —
code-verified); (c) for sampled S2 matches, recomputing the five P1
features, p_elo and the blend probability from data truncated to the
matches before them (in production (date, match_id) order — a
same-day earlier match is legitimately known) reproduces the
production `backtest_s2.csv` rows to machine precision. No leak was
found in any of the three checks.

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
2. **Matchday, after XI announcement (~30-60 min before the match),
   before the toss:** fill the XI CSV (format:
   `data/matchday/README.md`; starter file via
   `scripts/lock_matchday.py --make-example-xi <match_id>`) and run
   `python scripts/lock_matchday.py --xi-csv <file>`. It validates the
   XIs (11 per team, all in the team's squad in the player master, no
   duplicates, batting positions 1-11; **no overseas cap is enforced --
   no NPL playing-conditions rule for one was verified from an opened
   source**), computes XI strength from the CURRENT priors, and locks
   stage `P1_post_XI` at model v1.1 (temperature-calibrated blend).
   Actual announced XIs supersede the expected-XI selector -- this is
   the biggest real accuracy lever in the system.
3. **After the toss (~15 min before the match), before first ball:**
   `python scripts/lock_matchday.py --toss-csv <file>` (columns
   match_id,toss_winner,decision) locks stage `P2_post_toss` via the
   engine's contract-checked P2 path, adjusting the locked P1_post_XI
   (or the pre-season P1 if no P1_post_XI exists; the base stage is
   recorded in the row). The P2 adjustment is the Kirtipur chase
   premium estimated from S1+S2 (chasing teams won 33/63 decided
   matches, 52.4%; logit shift 0.095) -- small, because Kirtipur is not
   a dew-heavy outlier in our data. **First ball = freeze:** after it,
   no P1/P2 lock for that match is legitimate.
   `lock_matchday.py --dry-run` computes everything and writes locks
   only to a temp directory (verified 2026-10-24 on s3_2026_03:
   P1_post_XI 0.5004, P2_post_toss 0.5242 for the example toss,
   production log untouched).
4. **After the match:** the in-season update (cricsheet ingest -> normalize
   -> refresh_all) updates Elo and player priors, regenerates unlocked
   probabilities for remaining fixtures, and re-scores the frozen log.
   This happens when the match's cricsheet record has been published
   and ingested, which lags the match itself (see "Data publication
   lag"); until then, remaining fixtures are forecast from the ratings
   and priors as of the latest published match — the dashboard's
   Match Predictions page shows that as-of date ("Ratings as of"),
   stamped by `scripts/refresh_predictions.py` into
   `data/predictions/predictions_status.json`.
   Locked rows are never rewritten; `lock_predictions` refuses duplicates
   of (match_id, stage).

## Translation-factor estimation (Phase 2, Task A5)

The priors' per-league translation factors (how much of a player's
deviation from a foreign league's mean carries into the NPL) shipped
as documented assumptions (T20I 0.90; IPL/PSL/BBL/SA20 0.85; BPL/CPL/
LPL/ILT20/MLC 0.80). A5 tried to estimate them from overlap players
(>=60 decay-weighted balls in both the league and the NPL;
`scripts/estimate_translation.py`, results in
`data/predictions/translation_factors.json`). Findings: most leagues
have almost no qualifying overlap (BBL/IPL 4 overlap players, PSL 6,
LPL 7, CPL/SA20 8, with fewer than 3 usable observations in at least
one kind); BPL batting gives 2.74 on n=4; ILT20 0.03 (n=6) and MLC
-0.31 (n=3) have CIs spanning everything. T20I has real overlap
(n=40 combined) but estimates ~0.08 with a CI including 0 -- the pool
is confounded (Nepal internationals are below-mean in T20I and
above-mean in the NPL), so the estimate measures pool composition,
not translation. **No factor was changed** (update rule and reasoning:
Pre-registration Amendment #1). The assumptions stand, labelled as
assumptions, until more overlap seasons exist.

## Cross-league architecture check (Phase 2, Task A6)

The same architecture (canonical Elo + champion blend, priors-based
XI strength) was run walk-forward on the Lanka Premier League's most
recent season (LPL 2026; `scripts/cross_league_check.py`, results in
`data/predictions/cross_league_check.json`). 20 of 24 matches scored
(no-result / unusable lineups excluded). Blend: log-loss 0.6917,
Brier 0.2493, accuracy 50.0%. Higher-Elo baseline: 0.6859 / 0.2464 /
60.0%. Coin: 0.6931. Reading: the pipeline ports and behaves sanely
outside the NPL, and -- consistent with the NPL S2 backtest -- the XI
channel shows no measurable edge over Elo at this sample size; Elo
carries what signal exists. Caveats: different league strength
distribution and 5-team format; XI basis is post-hoc actual
participants (11-12 in the impact-player era), which flatters the XI
channel relative to the NPL's pre-season expected-XI locks; n=20 is
small. No NPL claim is updated by this check.

## Checkpoint rule (coefficients)

Logistic coefficients, blend weights and calibration are FROZEN during
the season except at two checkpoints: after S3 matches 10 and 20. At a
checkpoint a refit (pooled data, previous fit as prior) may be proposed;
it is promoted to champion only if it beats the frozen champion on
frozen-log log-loss over the matches since the previous checkpoint.
Otherwise the frozen model continues. Any promotion increments
MODEL_VERSION and starts a new frozen-log segment.

## Outcome rules for scoring (frozen 2026-10-24, before Match 1)

Defined before any Season 3 result exists, so no rule can be chosen
to flatter a score (review §4.2). Implemented in
`src/prediction/metrics.py: classify_outcome`, applied by
`scripts/score_predictions.py`:

- **Target outcome:** the official match winner as recorded by
  cricsheet (the ingested `winner_name` in the normalized matches).
- **Super over:** a tied match decided by a super over counts as a win
  for the super-over winner — if the source records the decider as the
  winner (or names an eliminator winner), the match is **scored** with
  that winner.
- **DLS / par score:** a result under DLS (or any par-score method)
  counts as a win for the officially declared winner — **scored**.
- **Tied with no decider, abandoned, no result:** the match is
  **excluded** from scoring — never scored as 0.5, never silently
  dropped. Each excluded fixture is recorded per match, with its
  reason, in `scorecard.csv` (`outcome_classification`,
  `exclusion_reason`) and counted in `scorecard_metrics.json` under
  `outcome_classification` (`excluded_tied_no_decider` /
  `excluded_no_result`, with the per-match list).
- Metrics (log-loss / Brier / accuracy) are computed over **scored
  matches only**, per stage as always. (Separately, the Elo engine
  still treats a tie as 0.5 for *rating updates* — that is a rating
  convention, not a prediction score, and the two are not mixed.)

## Season windows (two distinct concepts)

The tournament and the automation do not share one date range; keep
them separate (review §7.3):

- **Active fixture window: 2026-10-26 .. 2026-11-21.** The Season 3
  fixture dates themselves (28 league matches + 4 playoffs, final on
  2026-11-21), as recorded in `data/fixtures/s3_fixtures.csv`. All
  prediction locks, matchday capture and scoring refer to fixtures in
  this window. Nothing outside it is a Season 3 prediction.
- **Ingestion-retry / grace window: .. 2026-11-25.** Cricsheet
  publication lags real time by days, so the daily in-season update
  keeps running after the final: it stays silent before 2026-10-26,
  reports during the season, and makes a **final catch-up run after
  2026-11-25** (to land any late-published scorecards, including the
  final's) before the automation removes itself. This window is a
  property of the automation's gating (the `cricnepal-inseason-update`
  cron job definition), **not** of the fixture data — extending it
  never creates new fixtures, it only retries ingestion of existing
  ones.

## Data publication lag (F3 correction, 2026-10-24)

Earlier wording in this runbook (and in the pre-registration) said
ratings and priors "update after every match". That is the update
*rule*, not the cadence: an update can only run on data cricsheet has
published, and publication lags the match. The accurate statement,
used everywhere now: **ratings, priors and regenerated forecasts
update after every match whose cricsheet data has been published and
ingested.**

**Measured lag (Season 2).** For each of the 32 S2 matches in the
cricsheet NPL bundle, lag = the match file's `meta.created` date
minus the match date (`info.dates`). `meta.created` is the date
cricsheet created that match's record in its dataset — the best
available first-publication proxy (every S2 file is revision 1; S1
files were bulk-created on one date and are not used for this).
Results: **min 0, p25 1, median 8, p75 10, max 14 days** (mean 5.9).
Only 14/32 matches landed within 3 days; 27/32 within 10 days; all
within 14. The earliest matches were the fastest (the first five S2
matches: 0–1 days) — the long tail sits mid/late season. Treat these
as measured facts about S2's creation cadence, not a guaranteed S3
service level.

**Consequences for Season 3.** The original design assumption
(first S3 data ~Oct 29/30, i.e. 2–3 days after the opener) matches
the fast early-season pattern but not the median: at the S2 median,
a match's data lands ~8 days after it is played, so ratings and
priors may trail results by several matchdays, and forecasts for
upcoming fixtures are regenerated from the latest *published* state,
not the latest *played* state. The as-of labelling
(`predictions_status.json` + the dashboard's "Ratings as of" line)
exists precisely so this is visible rather than implied. The
matchday locks (P1_post_XI, P2_post_toss) are built from manually
captured XIs and toss results and do not wait for cricsheet.

## Provisional results (source-of-truth policy)

**Canonical source of truth: cricsheet.** Everything in the frozen
log's scoring, the priors and the end-of-season evaluation rests on
cricsheet records alone. But cricsheet publication lags the match
(Season 2 measured median **8 days**; see "Data publication lag"
above), which leaves an operational hole: for the first several
matchdays, and repeatedly through the season, played results exist
that the ratings cannot yet see. Policy (Pre-registration
Amendment #6, decided 2026-10-24, before Match 1): bridge the lag
with **provisional results**, under strict limits.

- **Winner only.** A provisional result records the winner of a
  fixture, captured manually from an official source (CAN / NPL
  official posts / broadcast) via `scripts/record_result.py`, with
  the source description and a capture timestamp (Asia/Kathmandu)
  in `data/results/provisional_results.csv`. Margin fields exist in
  the file and stay **blank** — no margin is captured, estimated or
  inferred.
- **Neutral margin.** Because no margin is known, a provisional
  match moves Elo with the margin-of-victory multiplier **1.0**
  (neutral): exactly what a margin-free canonical win would do.
  `src/prediction/provisional.py` (`MOV_PROVISIONAL = 1.0`).
- **Pure function, nothing stored.** Ratings including provisional
  results are recomputed from (ingested matches, fixtures,
  provisional file) every time: canonical current ratings first,
  then provisional results applied in fixture-date order with the
  canonical expected-score/update math. There is no incrementally
  maintained provisional rating to drift or corrupt.
- **Supersession.** The moment a fixture's match is ingested from
  cricsheet (matched on date + team pair), its provisional row is
  ignored by the computation — canonical data wins — and the
  refresh status (`predictions_status.json`) reports it under
  `provisional_superseded_match_ids`, recomputing ratings from
  canonical data alone (including the true margin).
- **Disagreement flagging.** If a provisional winner disagrees with
  the ingested winner once both exist, the refresh prints a WARNING
  and the status records it under `provisional_disagreements`. It is
  a data-quality flag for a human to resolve — never an exception
  that blocks the pipeline, and never silently resolved in either
  direction.
- **Corrections.** The provisional file is append-only. A wrong
  capture is fixed by appending a correction row
  (`scripts/record_result.py --supersede-correction "reason"`,
  marked `correction_of`); the last row per match is the effective
  one.
- **Locks record their basis.** Every matchday lock's
  `features_json` carries `ratings_basis` (`canonical` or
  `canonical+provisional`), `n_provisional_applied` and
  `data_as_of`. The dashboard's ratings caption shows
  "+ N provisional result(s)" when N > 0. A lock made on provisional
  state stays valid and identifiable as such forever — it is never
  rewritten when the canonical data arrives; the *next* locks use
  the reconciled ratings.

## End-of-season evaluation and error analysis (protocol)

After the final (and the grace-window catch-up, so the last results
have landed):

1. **Score the frozen log, per stage, never pooled** —
   `scripts/score_predictions.py`: log-loss (primary), Brier and
   accuracy for every locked stage (`P1_preseason_expected_xi`,
   `P1_post_XI`, `P2_post_toss`, `SIM_shadow_preseason`), each against
   its own baselines, with excluded matches reported under the outcome
   rules above. Paired-bootstrap 95% CIs (10,000 resamples, seed 42)
   for every model-vs-Elo log-loss difference — a point difference
   without its interval is not a result.
2. **Exploratory subgroup error analysis** — per-match log-loss broken
   down by: team; stage/horizon; toss decision (bat/field first);
   batting first vs chasing; and the fixture's XI data-quality flag
   (expected-XI unresolved-player count, as shown on the dashboard).
   **Labelled exploratory**: at n <= 32 every subgroup is a handful of
   matches, so subgroup patterns are hypotheses for next season's
   pre-registration, never conclusions and never a basis for in-season
   changes.
3. **Write it up against the pre-registration** — what was frozen,
   what the intervals say, which (if any) decision gates were met —
   before any Season 4 design discussion.

## Promotion decision gate (summary)

Promotion of any challenger (the shadow simulator, a checkpoint
refit, a new feature set) is governed by
`docs/PREREGISTRATION_S3.md` §3–§4 — the constants and thresholds live
there and are not duplicated here. In short, **no promotion without**:
(1) identical fixtures and horizon for champion and challenger;
(2) a leakage-clean comparison (as-of inputs, match-level time splits,
no tuning on the set being reported); (3) a paired-bootstrap interval
for the log-loss difference that excludes the pre-declared practical
threshold in the pre-registration; and (4) the comparison made on the
frozen prospective log, not on a reused backtest. If the gate is not
met, the frozen champion continues — a tie with Elo is a result, not
a failure.

## Data sources and known gaps

- Fixtures: league stage from the CAN fixture graphic via
  nepinsights.com, cross-checked with ipl.com (pairings/dates agree);
  playoff dates/stages from nepalontheweb.com's report of CAN's revised
  schedule, teams TBA. Start times are now recorded under CAN's revised
  timings of 2026-10-20 — see the fixture-time correction record below.
- Player details: roster + identity registry + enriched profiles (joined
  via registry surface forms). Registry IDs resolved for 110/133 players
  (101 exact name matches, 9 constrained initials-surname-unique matches
  flagged in `registry_id_match_type`); a pre-season resolution pass
  (2026-10-24, Pre-registration Amendment #2; audit trail in
  `data/predictions/player_resolution_log.csv`) resolved the two Sri
  Lanka internationals (Asalanka, Arachchige) on strong evidence. The
  unresolved 23 are mostly uncapped domestic players with
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

## Canonical forecast stages (G1, review §13, 2026-10-24)

The string "P1" historically named two different information sets:
the pre-season expected-XI locks and the matchday confirmed-XI
forecast. A horizon is part of the prediction itself, so the system
now names horizons canonically in exactly one place —
`src/prediction/stages.py` — and every reader (scoring, dashboard)
resolves stored strings through that registry. **Locked rows are
never rewritten**: the frozen log keeps its stored stage strings
forever; canonical names are the reporting layer. New locks keep
writing the existing stored strings, resolved through the registry
(`lock_matchday.py`, `predict_fixtures.py`).

| Canonical name | When issued | Permitted information | Stored as (frozen log) |
|---|---|---|---|
| `P0_PRESEASON` | Before the season (locked 2026-10-24, all 28 league fixtures) | Pre-season ratings, priors, expected XIs from the priors selector, form/rest from prior seasons. No toss, no announced XI, no S3 results. | `P1_preseason_expected_xi` |
| `P1_CONFIRMED_XI` | Matchday, after the official XIs are announced, before the toss | Everything in P0 with the expected XI replaced by the announced XI. Toss fields forbidden (engine-enforced). | `P1_post_XI` (engine contract alias: `P1`) |
| `P2_POST_TOSS` | Matchday, after the toss, before the first ball | Everything in P1 plus toss winner + decision (both required), with the pre-declared chase adjustment. | `P2_post_toss` (engine contract alias: `P2`) |
| `SIM_SHADOW` | Pre-season (locked 2026-10-24) | Expected XI, priors, ball-by-ball distributions. A shadow SYSTEM, not a horizon: scored separately, never the headline, never pooled with any horizon. | `SIM_shadow_preseason` |
| `INPLAY` | Continuously during a match | Current match state only. A separate SYSTEM (delivery-level), evaluated by its own harness, never locked in the frozen log. | — (not stored) |

Scoring (`scripts/score_predictions.py`) groups by canonical horizon:
aliases of one horizon can never split a score, horizons can never be
pooled, and an unregistered stage string raises instead of silently
forming a new category.

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
