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
| D4 | PASS | Batch 2 (1.2 + 7.1): served final layer regenerated from canonical by scripts/sync_final_from_normalized.py — exactly 8 team names/IDs served (tests/test_canonical_layer.py, 3 passed). Register now: CONF-001 RESOLVED with its resolution recorded; CONF-002 (team-ID split inside canonical) and CONF-003 (stored overs convention) open and surfaced; register rendered on the Season 3 Hub health section (7.1) |
| D5 | PARTIAL | Identity map explicit and logged; predict-time registry drop (I-03) still open — WAIVER-A task 4.1 |
| D6 | PASS | docs/DATA_DICTIONARY.md covers every inventoried dataset incl. Batch 2 artefacts; licences "not recorded" stated per dataset, never assumed. player_of_match POPULATED from the cricsheet bundle (plan 1.5): the bundle carries the field for all 64 matches; scripts/populate_player_of_match.py applied the ingest's semantics with a verified two-column diff (tests/test_player_of_match.py, 3 passed) |
| D7 | PASS | Batch 2 (1.3): silent defaults removed — metrics.compute_season_kpis/compute_team_kpis exclude missing/zero-innings rows from NRR and surface data_quality + exclusion counts; cards show "N/A / No innings data"; data_source transform keeps NaN innings summaries as NaN. tests/test_silent_defaults.py (6 passed; missing-overs hand-check +0.5 vs legacy −2.0). Real-data P0 pins unchanged (S1 +0.139, S2 −0.443) |

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
| P1 | PASS | Pre-match pinned (test_prematch_invariants) AND in-play invariants pinned on a real S2 match: tests/test_wpa_oos.py (probabilities in [0,1], terminal exactness, telescoping) |
| P2 | PASS | Plan 4.3 decision: batting-team perspective KEPT (consistent in code; referent flip at the break is by construction) and made explicit in the module docstring, the frozen page label and docs/MODEL_CARD.md; fixed-referent chain exported alongside (p_first_team_win) |
| P3 | PASS | Batch 2 (4.2): innings-2 chain opens at 1 − (innings-1 final p); test asserts equality on a real match |
| P4 | PASS | Decided innings-2 states forced to exactly 1.0/0.0 before chaining (_force_decided_states); synthetic + real-match tests |
| P5 | PASS | Telescoping exact by construction and tested: per-innings identities and Σ WPA (fixed-referent) = outcome − 0.50 over the whole match |
| P6 | PASS | Production WPA rebuilt walk-forward (train on strictly earlier dates only; leakage test: a match's probabilities are unchanged when later matches are removed); refresh path (module main) points at the OOS pipeline; exports carry .meta.json provenance (method walk_forward_by_match); legacy in-sample path retained for reproducibility and stamps its exports in_sample_legacy |

## Evaluation
| ID | Status | Evidence |
|---|---|---|
| V1 | PARTIAL | Live-path leakage guards strong; challenger in-sample caveat disclosed (task 5.4 pending) |
| V2 | PASS | Brier/log-loss/accuracy hand-tested (tests/test_prediction_metrics.py, 5 passed); clip aligned to [1e-6, 1-1e-6] with shipped numbers verified unchanged; reliability bins + ECE implemented (scripts/calibration_report.py → data/predictions/calibration_metrics.json) |
| V3 | PASS | Coin/Elo/chase baselines (backtest) + new in-play simple-logistic baseline (scripts/inplay_baseline.py → inplay_baseline_evaluation.json: S2 innings-2 LL 0.4137 vs WP model 0.4108) |
| V4 | PASS | Batch 2 (5.5): headline CIs plus (a) live S3 Hub scorecard champion−Elo paired bootstrap over scored matches (tests/test_bootstrap_ci.py, 4 passed) and (b) in-play WP-vs-baseline paired CI on 3,255 identical states: difference −0.0001, 95% CI [−0.0178, +0.0178] — not established (data/predictions/inplay_wp_vs_baseline_ci.json; surfaced in the Hub health section) |
| V5 | PASS | Standing "no demonstrated improvement over Elo" labels; docs/MODEL_CARD.md |
| V6 | PASS | Frozen log with timestamps/versions/inputs hash; immutability pinned by test_locked_fixtures_unchanged_in_regenerated_predictions |
| V7 | PASS | Fixed seeds; deterministic pipelines (audit) |

## Scouting
| ID | Status | Evidence |
|---|---|---|
| S1 | PARTIAL | Shrinkage applied; display of n/interval DONE (plan 6.1, Batch 2): Game Plan tables carry effective balls, prior-group evidence label and uncertainty with a legend (tests/test_evidence_display.py). Prior-construction changes remain plan 6.2 (WAIVER-A, not done) |
| S2 | PARTIAL | Brief template formalises the rule (docs/BRIEF_TEMPLATE.md); frozen opposition page still violates it (WAIVER-B) |
| S3 | PARTIAL | Written cards use opponent data; frozen page fails (plan 6.3, WAIVER-B) |
| S4 | PASS | No line/length data exists and none is claimed on live paths (audit) |
| S5 | PARTIAL | Validator built and run: scripts/validate_brief_numbers.py on brief_m04 traced 163/165 numbers; 2 flagged with causes (fall-of-wicket notation absent from capture CSVs; one prose hypothetical). Not yet a standing pre-publication gate |

## Dashboard / engineering
| ID | Status | Evidence |
|---|---|---|
| B1 | FAIL (by design) | Showcase freeze stands; restructure is WAIVER-B / post-season (plan 7.2) |
| B2 | PASS | Batch 2 (6.1, display-only): wherever the live Game Plan page shows a prior index it now also shows effective balls, the prior group as an evidence label, and the uncertainty value, with a one-line legend; no displayed number changed (priors pass through). Player Profiles shows observed aggregates only (no prior index) and already displays raw n — no change needed, rationale in worklog |
| B3 | PASS | Batch 2 (7.1 + 7.3): Data & Model Health section on the Season 3 Hub (dataset freshness, predictions_status staleness, conflicts register, model labels with CIs, B5 status) via pure load_health(); B3 behaviour tests (tests/test_hub_health.py, 6 passed): missing lock renders "—", a conflicts entry and a missing register each render visibly |
| B4 | PASS | Batch 2 (8.1, docs part): README states the single app command and single test command (verified on this VM); Makefile rewritten cross-platform (PYTHON variable, no .venv/Scripts/*.exe paths) and exercised end-to-end via `make test`. Launcher removal is WAIVER-B, out of scope |
| B5 | FAIL as specified | Suite has the 5 known-baseline failures; Batch 1 adds 21 passing tests and no new failures (full-suite record in docs/WORKLOG.md) |
| B6 | PASS | Data dictionary (updated for 1.2/1.5/5.5), model card (updated for 4.2/4.3/5.5), playing conditions, criteria matrix, plan, worklog, brief template, and a current README runbook (8.1) |
