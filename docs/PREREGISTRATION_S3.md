# Pre-Registration — NPL Season 3 Prediction System

**FROZEN 2026-10-24, before Match 1 of Season 3 (26 Oct 2026).**

This document records, in advance, every constant and rule that affects
Season 3 predictions, the evaluation protocol, and the locked stages.
Its purpose is to make tuning-after-the-fact impossible to hide: if a
constant changes during the season, the change is only legitimate as a
dated **amendment** appended at the bottom of this document (with the
reason and the before/after values). The original frozen text above the
Amendments section is never edited. A machine-readable copy lives in
`data/predictions/preregistration_s3.json`, and
`tests/test_phase2_accuracy.py` asserts the code constants equal the
pre-registered (amendment-adjusted) values — a drift alarm.

## 1. Frozen constants

### Elo (src/prediction/elo.py)
| Constant | Value |
|---|---|
| Initial rating | 1500 |
| K | 20 |
| Between-season regression (fraction of deviation from 1500 removed) | 0.40 |
| Margin-of-victory multiplier | 1 + 0.5 × min(1, \|run diff\| / 60), capped at 1.5 (MOV_CAP) |

### Champion blend, model v1 (src/prediction/model.py)
| Constant | Value |
|---|---|
| XI mapping scale (BLEND_K) | 2.0 |
| Elo weight (BLEND_W_ELO) | 0.5 |
| Probability clip | [0.05, 0.95] |
| P1 features | elo_diff, xi_batting_diff, xi_bowling_diff, form_nrr_diff, rest_diff |
| Challenger logistic | LogisticRegression C=1.0 on the P1 features (challenger only, never headline in v1) |

### Temperature calibration, model v1.1 (Phase 2, Task A2)
| Constant | Value |
|---|---|
| Method | Temperature scaling on the logit: p_cal = sigmoid(logit(p_raw) / T) |
| Temperature T (TEMPERATURE_V1_1) | 0.7496 |
| Fitted on | S2 walk-forward out-of-sample blend predictions (backtest_s2.csv, n=32), 2026-10-24 |
| OOS effect | Log-loss 0.68909 → 0.68882; Brier 0.24800 → 0.24791 (negligible; T within noise of 1.0 at n=32 — frozen as the honest fitted value, NOT claimed as an improvement) |
| Applies to | Future locks only (P1_post_XI and later stages). Locked v1 rows are never rewritten. |

### Player priors (src/prediction/priors.py)
| Constant | Value |
|---|---|
| History window | ~3 years (cutoff 2023-10-26), reference date 2026-10-26 |
| Decay half-life | 548 days (~18 months) |
| Shrinkage k, batting (K_BAT) | 150 balls |
| Shrinkage k, bowling (K_BOWL) | 120 balls |
| Translation factors t (deviation from source-league mean) | NPL 1.00, T20I 0.90, IPL 0.85, PSL 0.85, BBL 0.85, SA20 0.85, BPL 0.80, CPL 0.80, LPL 0.80, ILT20 0.80, MLC 0.80 (assumed, documented — see Amendment #1 for the estimation attempt) |
| Uncertainty | base = 1/sqrt(1 + total_balls/150); ×1.5 for external_pro and debutant groups |

### Expected-XI selection (src/prediction/engine.py)
Role score weights (bat/bowl index): Bowler 0.30/0.70; Batter and
Wicketkeeper 0.80/0.20; All-rounder 0.55/0.45. Constraints: at least 1
wicketkeeper (if the squad has one); at least 5 bowling options
(bowl_balls_eff ≥ 60 or role Bowler/All-rounder). No overseas cap is
imposed — no sourced NPL playing-condition for one was found.

### Form and rest features
Form = EWMA of per-match NRR, weights 0.75 (previous) / 0.25 (new match).
Rest days = days since last match, default 7 if none, capped at 14,
entered as a difference divided by 7.

### Monte Carlo simulator — SHADOW (src/prediction/simulator.py)
| Constant | Value |
|---|---|
| Outcome categories | runs {0,1,2,3,4,6} or wicket per legal ball; extras ignored (documented) |
| Shrinkage k, batting distributions (K_BAT_SIM) | 100 balls |
| Shrinkage k, bowling distributions (K_BOWL_SIM) | 120 balls |
| Dirichlet jitter | applied when batter or bowler has < 60 local balls in the phase; kappa = 25 + min(bat_n, bowl_n) |
| Production sims per match | 10,000 |
| Production seed | 20261026 + match_number (deterministic) |
| Phases | Powerplay (overs 1–6), Middle (7–15), Death (16–20) |

### Toss adjustment (P2)
Chase logit shift = **0.0953** (chasing teams won 33 of 63 decided
S1+S2 matches, 52.4%; estimated from S1+S2 by
`model.estimate_chase_logit`). Applied as +shift to the team batting
second, −shift to the team batting first, on the logit scale.

## 2. Three-system contracts (summary)

| System | Stages | Allowed inputs | Forbidden |
|---|---|---|---|
| Pre-match | P1_preseason_expected_xi, P1_post_XI, P1 | Ratings, XI strength from priors, form, rest (P1_post_XI also: announced XI) | Any toss field — enforced in code (`engine.STAGE_INPUTS`) |
| Toss-adjusted | P2_post_toss (contract name P2) | Everything in P1 + toss winner + decision (both required) | Locking without a valid toss |
| In-play | (continuous, not locked) | Current match state only | Pre-match inputs; evaluated separately, delivery-level, never pooled with P1/P2 |
| Shadow simulator | SIM_shadow_preseason | Expected XI, priors, ball-by-ball distributions | Toss fields; never the headline |

## 3. Checkpoint and promotion rules

- **Coefficients frozen in-season.** Logistic coefficients, blend
  weights, temperature and calibration change only at the checkpoints
  after S3 matches **10** and **20**: a refit (pooled data, previous fit
  as prior) may be proposed and is promoted **only** if it beats the
  frozen champion on frozen-log log-loss over the matches since the
  previous checkpoint. Otherwise the frozen model continues.
- **Simulator promotion:** the simulator stays shadow until it beats
  the champion on the **S3 frozen log** (log-loss, CI-aware: the
  paired-bootstrap 95% CI for the difference must exclude zero), never
  on a reused backtest.
- Elo ratings and player priors/posteriors update after every match
  via the in-season refresh; locked rows are never rewritten.

## 4. Scoring protocol

- Primary metric: **log-loss**. Also reported: Brier score, accuracy.
- Reported **per stage, never pooled** across stages or systems.
- Baselines per stage: coin flip (0.5), higher-Elo pick, chase
  heuristic (for P2: the toss-adjusted baseline is the locked P1).
- Differences between models are reported with paired-bootstrap 95%
  CIs (10,000 resamples, seed 42) — a point difference without its
  interval is not a result.
- Calibration is reported only in coarse bins; one 32-match season
  cannot certify calibration (see runbook, "Limits of a 32-match
  season").

## 5. Locked stages (as of freezing)

| Stage | Model version | Status at freeze |
|---|---|---|
| P1_preseason_expected_xi | v1 | 28 rows locked 2026-10-24 (expected XIs) |
| SIM_shadow_preseason | sim_v1 | 28 rows locked 2026-10-24 (shadow; scored separately, never headline) |
| P1_post_XI | v1.1 (temperature-calibrated) | Future: locked on matchdays from announced XIs via scripts/lock_matchday.py |
| P2_post_toss (contract P2) | v1.1 inputs + chase shift | Future: locked on matchdays after the toss via scripts/lock_matchday.py |

## 6. Amendment process

1. Never edit the frozen text above this section.
2. Append a dated amendment below, stating: what changed, the before
   and after values, the evidence/reason, and which already-locked rows
   (if any) used the pre-amendment values (they stay as locked).
3. Mirror the amendment in `data/predictions/preregistration_s3.json`
   (`amendments` array, with `field` and `after` values). The drift
   test computes effective constants as frozen values adjusted by
   amendments, so a code change without an amendment fails the suite.

## Amendments

### Amendment #1 — 2026-10-24 — Translation factors: estimation attempted (Task A5)

A5 estimated per-league translation factors from overlap players
(≥60 balls in both that league and the NPL; deviation-from-league-mean
regression through the origin; see
`data/predictions/translation_factors.json` and
`scripts/estimate_translation.py` for estimates, n and 95% CIs).
Update rule applied: combined overlap n ≥ 8 AND the estimate's CI
excludes the assumed value AND the CI excludes 0; updates are shrunk
toward the assumed value with N0 = 8.

**Outcome: no factor met the rule, so no translation factor was
changed.** The assumed factors in §1 stand, the priors were not
regenerated, and every locked row (including the A1 shadow rows, which
used exactly the §1 priors) is unaffected. Per league: BBL, CPL, IPL,
LPL, PSL and SA20 have fewer than 3 qualifying overlap observations in
at least one kind (no estimate possible); BPL's only estimate (batting,
n = 4) is 2.74 with CI [2.06, 3.42] — an n of 4 cannot move a factor;
ILT20 combined 0.03, CI [−0.57, 0.64], n = 6; MLC −0.31, CI [−2.50,
1.87], n = 3. T20I is the only league with adequate n (combined n = 40;
batting 0.10, CI [−0.21, 0.42]; bowling 0.03, CI [−0.35, 0.40]) — and
its near-zero estimate is the signature of a confounded pool (Nepal
internationals are below-mean against a world-class T20I pool and
above-mean in the NPL, which mechanically drives the estimate toward
zero); its CI includes 0, so it fails the rule and 0.90 is retained.
The honest conclusion: three seasons of overlap data cannot estimate
these factors yet; the documented assumptions stand, flagged as
assumptions.

<!-- Later amendments are appended below this line, dated, in order. -->

### Amendment #2 — 2026-10-24 — Player identity resolutions (pre-season hardening, review P0)

A resolution pass over the 25 S3 roster players whose
`cricsheet_registry_id` was unresolved at freeze, using strong evidence
only (cricsheet registry data from the downloaded bundles; name-variant
and initials analysis against that registry; full-name checks on
opened web sources for the two overseas internationals). Full audit
trail: `data/predictions/player_resolution_log.csv`.

**Resolved: 2 of 25** (both `initials_surname_unique`):
- **Charith Asalanka** (Biratnagar Kings) → `732c038e` ("KIC Asalanka",
  the only Asalanka in the cricsheet registry; full name Kariyawasam
  Indipalage Charith Asalanka → initials K.I.C.; 127 played Sri Lanka
  appearances in the local bundles, T20I debut 2021-07-25 vs India).
- **Sahan Arachchige** (Kathmandu Gorkhas) → `c05f9d20` ("SSD
  Arachchige"; full name Sahan Shashintha Diyamantha Arachchige →
  initials S.S.D.; the only other S-initial candidate, "S Arachchige",
  played for Italy in 2019 and is a different person).

**Still unresolved: 23.** Each was checked for exact, initials-form,
surname-unique and spelling-variant matches; the surname-unique
candidates that exist conflict on initials (e.g. the only registry
Paudel is "RK Paudel" — Rohit Paudel, not Krishna Paudel; the only
Poudel is "Krishna Poudel", not Aprajit Poudel) and the rest have no
registry presence at all — consistent with uncapped domestic players
with no cricsheet appearance yet. They stay unresolved, flagged, with
wider uncertainty; nothing was guessed.

**Effect:** priors were regenerated via `scripts/build_player_priors.py`.
Prior-group counts before → after: npl_experienced 91 → 91,
external_pro 14 → 16, debutant 28 → 26. Only the two resolved players'
prior rows changed (Asalanka: debutant → external_pro, 700.7 effective
bat balls; Arachchige: debutant → external_pro, 226.4). `player_history.csv`
is unchanged. **No constant changed.** All 56 already-locked frozen-log
rows (28 × P1_preseason_expected_xi v1, 28 × SIM_shadow_preseason
sim_v1) used the pre-amendment priors and stay exactly as locked;
future locks (P1_post_XI, P2_post_toss) use the amended priors — that
is the pre-registered design (priors update as information arrives;
locked rows never do).

### Amendment #3 — 2026-10-24 — Elo parameter-selection provenance (F1 audit)

**Finding.** The canonical Elo constants (K = 20, season regression
0.40) were selected from a grid evaluated on the Season 2 walk-forward
— the same S2 set that is then reported as the backtest evaluation.
That is selection-on-test, and it was not disclosed in §1. This
amendment records the provenance, bounds the resulting optimism, and
sets the standing rule. **No constant is changed by this amendment.**
Full artefact: `data/predictions/elo_selection_audit.json`
(`scripts/audit_elo_selection.py`).

**Provenance.** The grid code is `elo.tune_walk_forward`; the grid
actually searched at build time was the restricted research-range grid
invoked by `scripts/build_team_ratings.py` (K ∈ {20, 24, 28, 32} ×
regression ∈ {0.25, 0.33, 0.40}), scored on S2 walk-forward log-loss
(n = 32) and saved in `data/predictions/elo_tuning.csv` (recomputed
2026-10-24: every cell reproduces exactly). The shipped constants are
that grid's argmin: LL(20, 0.40) = 0.68885.

**Measured selection bound.** The restricted grid's S2 surface spans
only 0.68885–0.69380 (range **0.0050**); over the wider default grid
(K 16–40 × regression {0, 0.25, 0.33, 0.40, 0.50}) the surface spans
0.68697–0.70707 (range 0.0201; argmin (32, 0.50) at 0.68697). The S2
backtest numbers are therefore **mildly optimistic for Elo-family
models by at most the measured selection bound of 0.0050** (0.0201 as
a conservative outer envelope). Selection-adjusted, Elo's S2
log-loss could be as high as ≈ 0.6938 — i.e. even Elo's apparent edge
over the coin flip (0.6931) lies within the selection bound. The
champion blend's tie with Elo is unaffected as a comparison (both
were read off the same set), but no S2 number for an Elo-family model
should be quoted without this bound.

**Clean reselection.** Selecting K by walk-forward *within Season 1
only* chooses K = 28 (S1 log-loss 0.68454, vs 0.68493 at K = 20 — the
S1 surface is likewise flat). On S2, (28, 0.40) scores 0.68913 vs
0.68885 for (20, 0.40): worse by 0.00028, i.e. the **within-0.002
branch** of the decision rule. The between-season regression cannot
be selected within one season at all; its S2 slice at K = 20 (0.6964
at regression 0 → 0.6874 at 0.50; 0.6913–0.6888 across the research
range 0.25–0.40) is reported as sensitivity only, and **0.40 rests on
the research prior (regress 25–40% toward the mean between seasons),
not on clean selection**.

**Decision.** Keep (K = 20, regression = 0.40) for Season 3.
Switching constants mid-protocol for a within-noise difference
(0.00028) would be worse than the bounded bias, and the shipped pair
is also the restricted grid's argmin and the research-prior value.

**Effect on Season 3.** None on the frozen log: its parameters were
fixed before Match 1, so the prospective S3 test is uncontaminated.
The contamination is confined to the *historical evaluation claim*
(the S2 backtest), which now carries this bound wherever it is cited
(runbook, "parameter provenance" note).

**Standing rule (new).** Future parameter selection must be nested:
select on earlier seasons only, never on the season being reported
as the evaluation. A selection that touches the evaluation season
must be disclosed with its measured bound, as here.

### Amendment #4 — 2026-10-24 — Update-cadence correction (F3: cricsheet publication lag)

**Correction.** §3 of the frozen text says "Elo ratings and player
priors/posteriors update after every match via the in-season
refresh". Read literally, that claims a cadence the data source
cannot deliver: updates can only run on matches cricsheet has
published, and publication lags the match. The corrected statement,
in force from this amendment (and already applied to the runbook):
**ratings, priors and regenerated forecasts update after every match
whose cricsheet data has been published and ingested.**

**Measured lag.** For the 32 Season 2 matches in the cricsheet NPL
bundle, lag = the match file's `meta.created` date minus the match
date: **min 0, p25 1, median 8, p75 10, max 14 days** (mean 5.9);
14/32 within 3 days, 27/32 within 10 days. `meta.created` is
cricsheet's record-creation date for that match — the best available
first-publication proxy (all S2 files are revision 1); it is a
measurement of S2's creation cadence, not a guaranteed S3 service
level. The original design assumption (first S3 data ~Oct 29/30)
matches the fast early-season pattern (S2's first five matches
landed in 0–1 days) but **not** the median: at the S2 median, S3
ratings and priors will trail played results by several matchdays.

**Operational effect.** None on the protocol itself: the checkpoint
rule (matches 10 and 20) counts *played-and-ingested* S3 matches in
the frozen log's scoring, exactly as before; the frozen constants
are untouched; locked rows are unaffected. What changes is the
claim and its visibility: `scripts/refresh_predictions.py` now
stamps `data/predictions/predictions_status.json` (data_as_of =
latest published match date in the normalized data, plus the
ingested-match count) and the dashboard displays "Ratings as of"
next to the ratings table, so a forecast's information state is
never implied to be fresher than it is. The matchday locks
(P1_post_XI, P2_post_toss) use manual XI/toss capture and do not
depend on cricsheet at all. Full write-up: runbook, "Data
publication lag".

### Amendment #5 — 2026-10-24 — Canonical stage nomenclature (G1, review §13)

**Change (naming layer only — no constant, no rule, no locked row
changed).** The string "P1" named two different information sets:
the pre-season expected-XI locks (frozen §5: `P1_preseason_expected_xi`)
and the matchday confirmed-XI horizon (engine contract "P1", locked
as `P1_post_XI`). From this amendment, horizons carry canonical names
defined in exactly one place, `src/prediction/stages.py`:

| Canonical name | Stored stage string | Engine contract alias |
|---|---|---|
| `P0_PRESEASON` | `P1_preseason_expected_xi` | — |
| `P1_CONFIRMED_XI` | `P1_post_XI` | `P1` |
| `P2_POST_TOSS` | `P2_post_toss` | `P2` |
| `SIM_SHADOW` (shadow system) | `SIM_shadow_preseason` | — |
| `INPLAY` (separate system) | — (never locked) | — |

Scoring groups by canonical horizon and the dashboard displays
canonical labels (with the stored strings shown once, in the mapping
note); lock scripts resolve canonical → stored through the registry
and keep writing the existing stored strings. An unregistered stage
string now raises in scoring instead of silently forming a category.
The frozen §2/§5 tables keep the stored strings exactly as written —
this amendment adds the naming layer above them; it does not edit
them.

**Effect on locked rows:** none. All 56 locked rows keep their stored
stage strings and values; they are read through the mapping, never
rewritten. Future locks (P1_post_XI, P2_post_toss) write the same
stored strings as the frozen §5 table specifies.

### Amendment #6 — 2026-10-24 — Provisional results policy (source-of-truth)

**Change (operational policy added; no frozen constant, feature or
locked row changed).** Cricsheet is the canonical source of truth,
but its publication lag (Season 2 measured median 8 days, Amendment
#4) leaves played results invisible to the ratings for days at a
time. Decided 2026-10-24, before Match 1, on the review's §14
recommendation and the project owner's instruction:

- A **provisional result** may be captured manually from an official
  source (CAN / NPL official posts / broadcast) via
  `scripts/record_result.py`: fixture, **winner only**, source
  description, capture timestamp. Recorded in
  `data/results/provisional_results.csv` (append-only; corrections
  are new rows marked `correction_of`).
- Provisional matches move Elo with the margin-of-victory
  multiplier **1.0 (neutral)** — no margin is captured or estimated
  (`src/prediction/provisional.py`, `MOV_PROVISIONAL = 1.0`).
  Ratings including provisional results are a pure, recomputable
  function of (ingested matches, fixtures, provisional file):
  canonical ratings first, provisional wins applied in fixture-date
  order.
- **Supersession:** once a fixture is ingested from cricsheet, its
  provisional row is ignored (canonical wins, true margin applies)
  and reported as superseded in `predictions_status.json`. A
  provisional winner that **disagrees** with the ingested winner is
  flagged there as a data-quality warning — never silently
  resolved, never pipeline-blocking.
- **Locks record their basis:** every post-amendment lock's
  `features_json` carries `ratings_basis` (`canonical` /
  `canonical+provisional`), `n_provisional_applied` and
  `data_as_of`.

**Effect on locked rows:** none. All 56 rows locked before this
amendment (P0_PRESEASON `P1_preseason_expected_xi` v1 and
SIM_SHADOW `SIM_shadow_preseason` sim_v1) predate any provisional
data — their ratings basis is canonical, by construction and by the
calendar (the season had not started). Scoring of the frozen log is
unchanged: it uses cricsheet outcomes only, under the frozen
outcome rules.
