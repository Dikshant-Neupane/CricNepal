# PLAN — Corrections programme (from docs/WORKLOG.md loop, Section 1)

Ordered per the master prompt's priority: data integrity → cricket
arithmetic → eligibility → probability/WPA → evaluation honesty →
scouting → dashboard → docs. Full task text: the plan draft of
2026-10-29 (goal files). Status as of Batch 1 (2026-10-29):

## Batch 1 (this worktree, uncommitted, for Dikshant's gate review)
- [x] 0.1 Playing conditions → docs/PLAYING_CONDITIONS.md (E1)
- [x] 2.1 Single metrics module src/cricket/metrics.py + hand tests (C1–C6 groundwork)
- [x] 2.4 Official points table attempt → C5 BLOCKED (no official table published); secondary cross-check passes
- [x] 1.1 Conflicts register + check script (D4)
- [x] 1.4 Data dictionary + provenance → docs/DATA_DICTIONARY.md (D6)
- [x] 1.6 S3 scorecard-diff standing test, armed (D2)
- [x] 4.5 Pre-match invariant tests (P1, V6)
- [x] 5.1 Log-loss clip aligned to 1e-6 + hand tests (V2)
- [x] 5.2 Calibration reporting: reliability bins + ECE (V2)
- [x] 5.3 In-play simple-logistic baseline (V3)
- [x] 6.4 Brief evidence template + number validator (S2, S5)
- [x] 8.2 Model card → docs/MODEL_CARD.md (B6)
- [x] 8.3 Criteria matrix + plan + worklog (B6)

## Pending decisions (Dikshant)
- 0.2 WAIVER-A landing rule (match-10 / match-20 / post-season) for:
  2.2, 2.3, 3.1, 3.3, 4.1, 5.4, 6.2.
- 0.3 Fate of the frozen analytics estate (gates 1.2, 1.3, 2.5, 2.6,
  6.3, 7.2).
- Obtain the official NPL playing-conditions handbook from CAN
  (upgrades PLAYING_CONDITIONS.md from REPORTED-CORROBORATED).

## Next batches (after the decisions)
- Phase 1 rest: 1.2 canonical-layer reconciliation, 1.3 silent
  defaults, 1.5 player_of_match.
- Phase 2 rest: 2.5 consumer rewiring to src/cricket/metrics.py.
- Phase 4: 4.2 OOS WPA rebuild, 4.3 perspective decision, 4.4 refresh.
- Phase 5 rest: 5.5 CI coverage for quoted differences.
- Phase 6: 6.1 evidence display on live pages.
- Phase 7: 7.1 Data & Model Health surface (Hub section), 7.3 tests.
- Phase 8: 8.1 canonical runbook, 8.4 baseline-failure resolution
  (post-season).
