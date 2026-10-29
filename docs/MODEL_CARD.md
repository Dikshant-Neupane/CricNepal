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
wins. PERSPECTIVE DECISION (plan 4.3, 2026-10-29): the batting-team
perspective is KEPT — it is applied consistently (one target
definition in both innings; the referent team changes at the break
by construction), and the alternative fixed-referent chain is now
exported alongside it (p_first_team_win), under which the whole
match's WPA telescopes to outcome − 0.50 exactly. Both the code
docs and the page label state the perspective explicitly.

Production WPA was rebuilt out-of-sample (plan 4.2/4.4, 2026-10-29):
each match is scored by a model trained only on matches played on
strictly earlier dates (walk-forward; the 5 earliest matches, with
fewer than 4 predecessors, are not scored); decided innings-2
states are exactly 1/0; the innings-2 chain opens at 1 − (innings
1's final probability), not 0.50; exports carry a .meta.json
provenance sidecar (method: walk_forward_by_match). The legacy
in-sample construction is retained only as
compute_and_export_wpa() for reproducing historical artefacts and
stamps its exports in_sample_legacy.

Skill vs the simple baseline (plan 5.5): Batch 1's 3-feature
logistic baseline (runs needed, balls left, wickets in hand;
innings 2) scored S2 log loss 0.4137 on 3,471 undecided states vs
the WP model's aggregate 0.4108 on 3,503. The paired like-for-like
comparison (inplay_wp_vs_baseline_ci.json; 3,255 identical states,
32 matches): WP 0.4111 vs baseline 0.4115, per-match difference
−0.0001 with paired bootstrap 95% CI [−0.0178, +0.0178] — NO
demonstrated difference between the WP model and the 3-feature
baseline on current evidence.

## Known defects (audit IDs; fixes pending waiver decisions)
- I-01: no overseas cap in expected-XI selection (rule now sourced:
  docs/PLAYING_CONDITIONS.md) — WAIVER-A task 3.1.
- I-03: predict_fixture drops no-registry-ID players from XI strength
  instead of counting them at 1.0 — WAIVER-A task 4.1.
- I-04/I-05: FIXED 2026-10-29 (plan 4.2/4.3/4.4, Batch 2) — see
  the in-play section above; worktree exports regenerated with the
  walk-forward pipeline (deterministic, byte-identical on re-run).
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
