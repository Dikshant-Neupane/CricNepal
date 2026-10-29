# CRITERIA MATRIX (master prompt Section 9)

Created 2026-10-29 from the implementation audit's criteria snapshot;
updated for corrections Batch 1 (worktree corrections/2026-10-29,
uncommitted). Evidence = test name + command + result, or file path.
Commands run with ~/workspace/.scratch/cric-audit-venv/bin/python.

## Data integrity
| ID | Status | Evidence |
|---|---|---|
| D1 | PASS | Audit §5 recomputation (all 64 matches); src/cricket/metrics.py innings_summary + tests/test_cricket_metrics.py (pytest: 9 passed) |
| D2 | PASS (S1/S2) / ARMED (S3) | Audit scorecard rebuild; scripts/s3_scorecard_diff.py — capture-internal diff 0 discrepancies over Matches 1–4; cricsheet side activates when S3 publishes. tests/test_s3_scorecard_diff.py |
| D3 | PASS | Audit recomputation: zero winner/margin discrepancies in canonical data |
| D4 | PARTIAL | Register built: data/conflicts_register.csv via scripts/check_conflicts.py (CONF-001 + 4 winner-spelling rows, all "surfaced, not resolved"). UI surfacing pending plan 7.1 |
| D5 | PARTIAL | Identity map explicit and logged; predict-time registry drop (I-03) still open — WAIVER-A task 4.1 |
| D6 | PARTIAL | docs/DATA_DICTIONARY.md covers every inventoried dataset; licences largely "not recorded" (stated, not assumed); player_of_match null 64/64 (plan 1.5) |
| D7 | FAIL | I-09 silent defaults in dashboard KPI path untouched (plan 1.3, gated). Master missingness itself is exemplary |

## Cricket arithmetic
| ID | Status | Evidence |
|---|---|---|
| C1 | PASS (module) | tests/test_cricket_metrics.py::test_overs_notation_never_float_arithmetic, test_phase_boundaries, test_ball_accounting. Legacy consumers rewired under plan 2.5 |
| C2 | PASS (module) | test_innings_attribution_hand_example: batter 14, bowler 16, extras 5 split by type, byes/leg-byes excluded from bowler |
| C3 | PARTIAL | Module set correct and tested (test_bowler_credited_wicket_set); priors pipeline still counts retired out — WAIVER-A task 2.2 |
| C4 | PARTIAL | Module returns None for undefined averages/rates (test_rates_and_undefined_cases); dashboard/research averages not re-verified case-by-case |
| C5 | BLOCKED | No official CAN/NPL points table is published (attempts in docs/WORKLOG.md 2.4). Secondary cross-check PASSES: module reproduces all 8 cricnepal.com S2 league NRRs within ±0.002 (test_nrr_s2_secondary_crosscheck) and Janakpur S1 +0.139 (test_nrr_janakpur_s1_regression) |
| C6 | PARTIAL | Single module exists (src/cricket/metrics.py); duplicates not yet deleted (plan 2.5) |

## Rules / eligibility
| ID | Status | Evidence |
|---|---|---|
| E1 | PARTIAL | docs/PLAYING_CONDITIONS.md with citations: overseas/XI rules REPORTED-CORROBORATED from CAN officials via 3+ outlets; official handbook NOT VERIFIED; impact and tie-break rules NOT VERIFIED |
| E2 | FAIL | Cap not enforced in selector or lock validation; enforcement is WAIVER-A task 3.1 now that the rule is sourced |
| E3 | PARTIAL | Bowler 4-over / no-consecutive-overs enforced in simulator only (audit) |

## Probability / WPA
| ID | Status | Evidence |
|---|---|---|
| P1 | PARTIAL | Pre-match pinned by tests/test_prematch_invariants.py (5 passed); in-play invariants untested |
| P2 | FAIL (in-play) / PASS (pre-match) | Audit R-analysis; unchanged in Batch 1 (plan 4.3) |
| P3 | FAIL | Innings-2 baseline reset (audit R1); plan 4.2 gated |
| P4 | FAIL | Terminal p never exactly 1/0 (audit R1); plan 4.2 |
| P5 | FAIL | Σ WPA telescopes to (final p − 0.5) per innings (audit R1); plan 4.2 |
| P6 | FAIL | Production WPA in-sample (I-04), exploratory label as mitigation; plan 4.2/4.4 |

## Evaluation
| ID | Status | Evidence |
|---|---|---|
| V1 | PARTIAL | Live-path leakage guards strong; challenger in-sample caveat disclosed (task 5.4 pending) |
| V2 | PASS | Brier/log-loss/accuracy hand-tested (tests/test_prediction_metrics.py, 5 passed); clip aligned to [1e-6, 1-1e-6] with shipped numbers verified unchanged; reliability bins + ECE implemented (scripts/calibration_report.py → data/predictions/calibration_metrics.json) |
| V3 | PASS | Coin/Elo/chase baselines (backtest) + new in-play simple-logistic baseline (scripts/inplay_baseline.py → inplay_baseline_evaluation.json: S2 innings-2 LL 0.4137 vs WP model 0.4108) |
| V4 | PASS (headline) | Paired bootstrap CIs on headline comparisons; extension to all quoted diffs is plan 5.5 |
| V5 | PASS | Standing "no demonstrated improvement over Elo" labels; docs/MODEL_CARD.md |
| V6 | PASS | Frozen log with timestamps/versions/inputs hash; immutability pinned by test_locked_fixtures_unchanged_in_regenerated_predictions |
| V7 | PASS | Fixed seeds; deterministic pipelines (audit) |

## Scouting
| ID | Status | Evidence |
|---|---|---|
| S1 | PARTIAL | Shrinkage applied; display of n/interval pending plan 6.1/6.2 |
| S2 | PARTIAL | Brief template formalises the rule (docs/BRIEF_TEMPLATE.md); frozen opposition page still violates it (WAIVER-B) |
| S3 | PARTIAL | Written cards use opponent data; frozen page fails (plan 6.3, WAIVER-B) |
| S4 | PASS | No line/length data exists and none is claimed on live paths (audit) |
| S5 | PARTIAL | Validator built and run: scripts/validate_brief_numbers.py on brief_m04 traced 163/165 numbers; 2 flagged with causes (fall-of-wicket notation absent from capture CSVs; one prose hypothetical). Not yet a standing pre-publication gate |

## Dashboard / engineering
| ID | Status | Evidence |
|---|---|---|
| B1 | FAIL (by design) | Showcase freeze stands; restructure is WAIVER-B / post-season (plan 7.2) |
| B2 | PARTIAL | I-12 display gaps open (plan 6.1) |
| B3 | PARTIAL | Hub/predictions handle missing locks honestly; general stale/conflict surfacing pending 7.1/7.3 |
| B4 | FAIL | Canonical run command not yet fixed (plan 8.1) |
| B5 | FAIL as specified | Suite has the 5 known-baseline failures; Batch 1 adds 21 passing tests and no new failures (full-suite record in docs/WORKLOG.md) |
| B6 | PARTIAL | Now present: data dictionary, model card, playing conditions, criteria matrix, plan, worklog, brief template. README/runbook currency pending 8.1 |
