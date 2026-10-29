# WORKLOG — Corrections programme (Batch 1, 2026-10-29)

Per the upgraded master prompt Section 1, every change is recorded here:
understand → specify → hand-check → test first → implement → verify.

Isolation: all work in the git worktree `~/workspace/cricnepal-corrections`
(branch corrections/2026-10-29). Nothing is committed or pushed; the main
tree's in-season matchday operations are untouched. Frozen log md5 at
start: `1bebae9831038ea9137f2fb1d2e0b0d4`.

WAIVER-A tasks are OUT of this batch and remain pending Dikshant's
landing decision (plan 0.2): 2.2 priors retired-out fix, 2.3 match_nrr
fix, 3.1 overseas-cap enforcement, 4.1 reg_ids fix, 5.4 challenger
artefact, 6.2 priors interval column. WAIVER-B (navigation/showcase)
also out.

---

## 0.1 Playing conditions (E1)

UNDERSTAND: the repo contains no playing-conditions document; the
blueprint assumes a max-4-overseas XI rule without a source (audit I-02).
SPECIFY: settle from an authoritative source (CAN / NPL official):
max overseas in XI, squad/registration limits, impact/substitute rule,
tie-break rule.
RESEARCH (2026-10-29, web): no official CAN/NPL playing-conditions
handbook could be found. Sources attempted: CAN official site
(cricketnepal.org.np press releases — procurement notices only, no NPL
playing conditions), NPL site reporting, Kathmandu Post, Nepal News,
Makalu Khabar, Sportstar. The overseas rules ARE consistently reported
by at least three independent outlets (Kathmandu Post 2026-10-23 and
2026-10-25/26; Nepal News; Makalu Khabar), each attributing them to CAN
Secretary Paras Khadka's statements at CAN's pre-season press
conference: Season 3 squad 6–8 overseas including at least one ICC
Associate-nation player; playing XI maximum 4 overseas (at least 7
Nepali players); overseas players (including retired) need an NOC from
their home board; Seasons 1–2 squads carried 4–6 overseas. Impact /
substitute rule: no source found — NOT VERIFIED. Tie-break rule: no
authoritative source found — NOT VERIFIED.
RECORD: docs/PLAYING_CONDITIONS.md written with per-rule status labels
and citations. Status: overseas/XI rules REPORTED-CORROBORATED (official
handbook NOT VERIFIED); impact and tie-break NOT VERIFIED.

## 2.4 Official points table (C5)

RESEARCH: no official CAN/NPL-published S1 or S2 points table could be
located (CAN site carries none). Secondary tables exist and disagree
with each other (cricnepal.com S2 final: Janakpur NRR −0.443;
possible11: −0.458 — the cricnepal.com figures are internally
consistent with its own For/Against columns; possible11's are not).
VERDICT: C5 is BLOCKED on an official table. As a secondary cross-check
(not C5), the new metrics module's S2 NRRs are compared against the
cricnepal.com published table in tests/test_cricket_metrics.py.

## 2.1 Single metrics module (C1–C6)

UNDERSTAND: rates are re-implemented across priors, dashboard services,
frozen analytics and a dead legacy NRR function (audit §4, I-06/I-09).
SPECIFY: Section 4 definitions exactly (see module docstrings).
HAND-CHECK: a 10-delivery innings worked by hand (see
tests/test_cricket_metrics.py): batter runs 14, extras 5 (wide 1,
no-ball penalty 1, leg-bye 1, byes 2), team total 19, legal balls 8,
balls faced 9, bowler runs conceded 16 (byes/leg-byes excluded),
bowler-credited wickets 1 (bowled; the run out is not credited),
economy 12.0. All-out NRR hand case: 100 all out in 12 overs counts as
20 overs faced.
TEST FIRST: tests/test_cricket_metrics.py written before the module;
first run fails with ModuleNotFoundError (recorded below), then passes
after implementation.
IMPLEMENT: src/cricket/__init__.py + src/cricket/metrics.py (new code
only; no consumer rewired — rewiring is plan 2.5, gated).
VERIFY: see the verification section at the end of this log.

VERIFY (2.1): hand-example tests passed after implementation; the
Janakpur S1 regression reproduces +0.139 (not +0.452). The S2
secondary cross-check initially mismatched for exactly the four
playoff teams; the published table is a league-stage table, so the
check is scoped to League matches, after which all 8 teams match the
cricnepal.com table within ±0.002. One implementation fix during
verification: parquet NaN extras/dismissal fields are normalised as
absent (the hand examples used None).

## 5.1 Prediction metrics clip + hand tests (V2)

UNDERSTAND: src/prediction/metrics.py clips log loss at EPS = 1e-15;
the prompt specifies [1e-6, 1-1e-6]. All shipped probabilities are
already clipped to [0.05, 0.95] upstream, so the change cannot move
any shipped number; verified by recomputing the S2 backtest metrics
from data/predictions/backtest_s2.csv before and after.
TEST FIRST: tests/test_prediction_metrics.py — the clip test fails
against EPS = 1e-15 (log_loss([1.0],[1]) returns ~0 instead of
-ln(1-1e-6)); Brier/log-loss/accuracy hand examples pass both before
and after. Then EPS aligned to 1e-6.

## 1.1 Conflicts register (D4)
scripts/check_conflicts.py (read-only) compares the normalized and
final match layers and writes data/conflicts_register.csv: CONF-001
(Kathmandu Gurkhas/Gorkhas identity split) plus exactly the 4
winner-name spelling diffs the audit found. Nothing is resolved;
status on every row is "open — surfaced, not resolved".

## 4.5 Pre-match invariants (P1, V6)
tests/test_prematch_invariants.py pins: probabilities in [0,1]
wherever present (SIM shadow rows legitimately carry no challenger
value — missing stays missing), complementarity, unique
(match_id, stage) locks, and locked P1 rows identical in the
regenerated upcoming_predictions.csv. 5 passed.

## 1.6 S3 scorecard diff (D2)
scripts/s3_scorecard_diff.py + tests/test_s3_scorecard_diff.py:
capture-internal diff (batting/bowling lines vs innings facts) is
clean for Matches 1–4 (0 discrepancies); the cricsheet side reports
ARMED (0 S3 matches published yet) and activates automatically.

## 5.2 Calibration (V2) and 5.3 in-play baseline (V3)
scripts/calibration_report.py → data/predictions/
calibration_metrics.json: ECE champion 0.1495, Elo 0.1445, raw
logistic 0.2131, simulator 0.2115 (32 matches each); in-play baseline
0.0859 (3,471 deliveries). WP-model calibration NOT PRODUCED (its
harness stores aggregates only; noted in the artefact).
scripts/inplay_baseline.py → inplay_baseline_evaluation.json: the
3-feature logistic (runs needed, balls left, wickets in hand),
train S1 / test S2 innings 2: LL 0.4137, Brier 0.1320, accuracy
0.8139 (n=3,471 undecided states) vs the WP model's stored
innings-2 aggregates LL 0.4108 / Brier 0.1319 / accuracy 0.8119
(n=3,503). On current evidence the WP model's innings-2 skill is
indistinguishable from the simple baseline — recorded in
docs/MODEL_CARD.md.

## 6.4 Brief template + validator (S2, S5)
docs/BRIEF_TEMPLATE.md formalises observation → evidence →
limitation → action. scripts/validate_brief_numbers.py run over
brief_m04.md against its source files: 163/165 numbers trace
(directly, by rounding, by targeted derivation — economies, per-ball
rates, innings run rate — or as probability complements). The 2
untraced are correctly flagged for human review: "4.4" (fall-of-
wicket over notation present in the source scorecard text but not
in the capture CSVs) and "125" (a prose hypothetical, not data).

## 1.4, 8.2, 8.3 Docs
docs/DATA_DICTIONARY.md (every inventoried dataset with source,
licence position, freshness), docs/MODEL_CARD.md, docs/PLAN.md,
docs/CRITERIA_MATRIX.md (audit snapshot updated per Batch 1 task).

## Verification (Batch 1)
- New tests: 21 passed (9 cricket metrics + 5 prediction metrics +
  5 pre-match invariants + 2 scorecard diff).
- Full suite in this worktree: 414 passed, 5 failed, 13 skipped
  (41.5s) - the 5 failures are exactly the known-baseline set
  (coach_shadow frozen-log pin, hardening manifest, provisional
  policy, registry mapping, hub lock-stage); the 13 skips are tests
  for gitignored generated deliverables absent from a fresh worktree.
  No new failures.
- frozen_log.csv md5 unchanged: verified at the end of the batch.
