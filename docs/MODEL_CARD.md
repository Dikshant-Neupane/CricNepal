# Model Card — CricNepal prediction system (plan task 8.2)

Distilled 2026-10-29 from docs/PREDICTION_SYSTEM.md and the
implementation audit. The pre-registration (docs/PREREGISTRATION_S3.md)
governs scoring; this card describes, it does not amend.

## What it predicts
Pre-match win probability for the first-named team, in frozen stages:
P1 (pre-season / post-XI, expected or announced XIs), P2 (post-toss),
plus two shadow series (SIM simulator, COACH_SHADOW) that are scored
alongside and never blended.

## Champion model
Logistic blend of: Elo difference (canonical Elo, src/prediction/
elo.py), XI batting/bowling strength differences from shrunk player
priors, form NRR difference, rest difference. Temperature calibration
v1.1 (T = 0.7496) fitted on S2 walk-forward out-of-sample predictions
only; its own record states the gain is negligible and it must not be
described as an improvement.

## Evaluation (Season 2 walk-forward, out-of-sample, 32 matches)
- Champion: log loss 0.689088, Brier 0.248003, accuracy 46.9%.
- Elo alone: log loss 0.688848, Brier 0.248013.
- Paired bootstrap 95% CI for the difference includes zero.
- **Label (mandatory wording): no demonstrated improvement over Elo.**
- Calibration (Batch 1, data/predictions/calibration_metrics.json):
  champion ECE 0.1495, Elo 0.1445 on 32 matches — small-sample
  values, reported with their bin counts.

## In-play model (separate system, frozen pages)
State-feature logistic models per innings, target = batting team
wins (perspective flips at the innings break — audit I-05). Its
out-of-sample evaluation (train S1, test S2, delivery-level) exists
(inplay_wp_evaluation.json), but the production WPA export is
IN-SAMPLE (I-04) and labelled exploratory. Batch 1 added the
prompt-required simple-logistic baseline (runs needed, balls left,
wickets in hand; innings 2): S2 log loss 0.4137 / Brier 0.1320 /
accuracy 0.8139 on 3,471 undecided states, versus the WP model's
innings-2 stored aggregates 0.4108 / 0.1319 / 0.8119 on 3,503
deliveries — i.e. the WP model's innings-2 performance is
indistinguishable from the 3-feature baseline on current evidence.

## Known defects (audit IDs; fixes pending waiver decisions)
- I-01: no overseas cap in expected-XI selection (rule now sourced:
  docs/PLAYING_CONDITIONS.md) — WAIVER-A task 3.1.
- I-03: predict_fixture drops no-registry-ID players from XI strength
  instead of counting them at 1.0 — WAIVER-A task 4.1.
- I-04/I-05: in-sample production WPA; innings-2 baseline reset;
  batting-team perspective — plan tasks 4.2/4.3 (gated).
- I-06: model.match_nrr ignores the all-out rule (correct Janakpur
  S1 NRR +0.139 vs +0.452 approximated) — WAIVER-A task 2.3. The
  correct implementation now exists in src/cricket/metrics.py and
  reproduces all 8 published S2 league NRRs (secondary source).
- I-11: priors count "retired out" as bowler-credited — WAIVER-A 2.2.
- Challenger artefact is fitted on S1+S2 with trained_on disclosed
  (task 5.4).

## Freezing and provenance
Every lock records timestamp, model version and a features_json
inputs hash (V6 PASS). The frozen log is append-only; historic rows
are never recomputed with later data. Fixed seeds in bootstrap and
simulator audit (V7 PASS).
