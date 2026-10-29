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

---

# Batch 2 (2026-10-29) — plan tasks 1.3, 6.1, 7.1+7.3, 5.5, 4.2+4.4,
# 4.3, 1.2, 1.5, 8.1. Worktree only, uncommitted for gate review.
# No WAIVER-A/B work; PREREGISTRATION_S3.md untouched; frozen log
# md5 verified unchanged at batch end.

## 1.3 Kill the silent defaults (D7)
Understand: compute_season_kpis replaced missing overs with 20.0 and
compute_team_kpis fillna'd to 0/20.0, and the data_source transform
turned NaN innings summaries into 0 runs / 20.0 overs — a missing
innings silently became a real one in every NRR.
Specify: a row contributes to NRR only when all four summary inputs
are present and both overs > 0; excluded rows are counted and
surfaced (data_quality, nrr_missing_rows, nrr_no_innings_rows,
nrr_excluded); cards render "N/A / No innings data".
Hand-check: a 2-match case with one missing-overs row must give NRR
+0.5 from the valid match alone (legacy code: −2.0); a no-result row
must not drag NRR (+0.5, legacy +0.25).
Test first: tests/test_silent_defaults.py (6 tests) failed pre-fix.
Implement: src/dashboard/services/metrics.py (_nrr_aggregation,
None-safe delta) and the data_source transform (NaN summaries stay
NaN). Verify: 28 passed incl. the P0 real-data pins — on current
real data NO displayed number changes (the backfill supplies real
summaries); numbers change only where data is genuinely missing,
which is the point: they previously showed fabricated values.

## 6.1 Show the evidence on live pages (B2, S1-display)
Game Plan team tables gain "Bat balls (eff)" / "Bowl balls (eff)",
an "Evidence" column (prior group) and "±" (uncertainty), plus a
legend caption (group semantics taken from src/prediction/priors.py:
npl_experienced = NPL record; external_pro = external-only history,
1.5x uncertainty; debutant = league-mean prior, 1.5x). Display-only:
every pre-existing number passes through unchanged (test pins it).
Player Profiles: NO change — it displays observed career aggregates
only (no prior index anywhere on the page) and already shows raw n
(balls faced/bowled). tests/test_evidence_display.py (3 passed).

## 7.1 + 7.3 Data & Model Health on the Hub (B3, D4-surfacing)
Pure load_health(root) in season3_hub.py: per-dataset freshness,
predictions_status with a stale flag (a played match newer than
data_as_of), conflicts register rows verbatim, model labels with
the champion-vs-Elo bootstrap CI and the "no demonstrated
improvement" label, and B5 status parsed from the criteria matrix.
Rendered as a Hub section (nav untouched). B3 tests
(tests/test_hub_health.py, 6 passed): stale status + conflict
surfaced; empty-root degradation; AppTest — missing lock renders
"—", a conflict entry renders visibly, a missing register renders
a visible warning.

## 5.5 Bootstrap CIs everywhere a difference is quoted (V4)
Headline CIs already existed (backtest_metrics.json, quoted on the
Predictions page). Two gaps closed: (a) the live S3 Hub scorecard
now carries the champion−Elo paired bootstrap over scored matches
(_champion_vs_elo_ci, match-level resampling, fixed seed;
tests/test_bootstrap_ci.py, 4 passed); (b) the in-play WP-vs-
baseline difference got a like-for-like paired CI —
scripts/inplay_difference_ci.py pairs both systems on 3,255
identical undecided innings-2 states over 32 matches: WP 0.4111 vs
baseline 0.4115, per-match difference −0.0001, 95% CI
[−0.0178, +0.0178], includes zero — no demonstrated difference.
Artefact: data/predictions/inplay_wp_vs_baseline_ci.json, surfaced
in the Hub health section and recorded in docs/MODEL_CARD.md.

## 4.2 + 4.4 WPA production path rebuilt out-of-sample (P1, P3–P6)
Separation verified first: nothing in the S3 prediction path
imports win_probability_model (refresh_all runs it as a standalone
step; the evaluation harness uses the class directly).
Specify: predict_walk_forward trains only on matches played on
strictly earlier dates (same-date matches never train each other);
a match with fewer than 4 earlier matches is not scored — its
probabilities stay absent, never filled. _force_decided_states sets
decided innings-2 states to exactly 1.0/0.0. add_wpa_columns chains
WPA with innings 1 opening at 0.50 and innings 2 opening at
1 − (innings-1 final p). Exports carry a .meta.json provenance
sidecar; the module main() (what refresh_all invokes) now runs the
OOS pipeline; the legacy in-sample function is retained, labelled,
and stamps its exports in_sample_legacy.
Tests (tests/test_wpa_oos.py, 4 passed): walk-forward coverage and
a leakage test (a match's probabilities are identical when later
matches are removed); decided-state forcing; on a real S2 match —
P1 probabilities in [0,1], P4 terminal p exactly the outcome, P3
innings-2 opening equality, P5 telescoping per innings and
Σ WPA = outcome − 0.50 on the fixed-referent chain.
Regeneration: worktree exports regenerated with the new pipeline;
deterministic (byte-identical md5 on re-run). Diff vs the in-sample
export is fully explainable: 13,828 deliveries / 59 matches (the 5
earliest matches have < 4 predecessors and are unscored, recorded
in the sidecar); mean |Δp| 0.0785 on shared deliveries; leaderboard
top-10 overlap 6/10. The MAIN repo's exports regenerate on the
first refresh after this batch lands.

## 4.3 Perspective decision (P2)
Decision: KEEP the batting-team perspective. Reasoning: the code
applies it consistently (one target definition in both innings);
the "flip" is the definition working as intended, not an
inconsistency. The Batch 1 model card's stronger claim is
superseded by this analysis. Made explicit in the module docstring,
the frozen page's WPA_NOTE, and docs/MODEL_CARD.md; a fixed-referent
chain (p_first_team_win) is exported alongside, on which the whole
match telescopes to outcome − 0.50 exactly.

## 1.2 Canonical data layer (D4)
Declare: data/normalized canonical (src/config/paths.py comment,
docs/DATA_DICTIONARY.md); data/final/parquet is a served projection
regenerated by scripts/sync_final_from_normalized.py.
Findings during implementation (all registered): the final matches
copy was stale (innings summaries all-NaN) and split Kathmandu
across two spellings; the canonical spelling is "Kathmandu Gorkhas".
A second spacing variant ("Sudur Paschim Royals") existed in
player_innings. Normalized's own team-ID columns carry both
Kathmandu IDs (CONF-002, open; served copies aligned; ingest fix is
post-season — the canonical source is not hand-patched mid-season).
Normalized's stored innings overs violate the NRR convention on 50
of 128 innings (CONF-003, open): served with stored values,
Janakpur's S1 NRR reads +0.492 instead of the verified +0.139, so
the served matches copy carries summaries derived from the
canonical ball-by-ball under the same convention the dashboard
backfill has always applied — served numbers are identical to
before the sync (P0 test proves +0.139/−0.443 through the file
itself now). Two implementation breaks were caught by the suite and
fixed in the sync, not in consumers: served innings wickets keep
the legacy float64 dtype (the ingest append path aligns fresh rows
against served dtypes and rejects NaN→int64 casts), and
tests/test_prematch_invariants.py's register assertion was updated
to the post-resolution truth (CONF-001 present as RESOLVED with its
resolution; CONF-002 open) — the register still surfaces, it no
longer claims an unresolved state that 1.2 fixed.
Verify: tests/test_canonical_layer.py (3 passed): exactly 8 team
names and 8 team IDs served; final matches equal canonical on
identity/results; served overs equal the derivation per innings.
Before/after served snapshot: Kathmandu matches 15, wins unified
5+4 → 9 under Gorkhas; innings-1 runs nulls 64 → 0.

## 1.5 player_of_match (D6) — CORRECTED after direct source check
Initial pass (inference): the ingest captures info.player_of_match
when present (fixture-proven), yet the stored canonical layer was
null 64/64 — I inferred the bundle lacked the field and retired it
in the data dictionary. That inference was WRONG. The bundle
(npl_json.zip, located afterwards in the priors build cache) was
then read directly: all 64 match JSONs carry player_of_match.
Corrected decision: POPULATE. scripts/populate_player_of_match.py
applies the ingest's exact semantics (first listed name, raw
surface form; id slug identical to ingest_cricsheet.slug) to the
canonical table; the write asserts every match has a bundle value
and verifies no other column changed (independent re-check:
exactly player_of_match and player_of_match_id differ; nulls
64 → 0). Spot values read from the bundle: espn_1462596 BKEL
Milantha, espn_1462640 Sohail Tanvir, espn_1462642 DS Airee —
pinned in tests/test_player_of_match.py (3 passed). Displayed
effect: the frozen Match Review page now shows the actual POTM
name instead of a dash for S1/S2 matches — the intended result of
populating real source data. The served final copy inherits the
columns via the 1.2 sync.

## 8.1 Canonical runbook, docs part (B4, B6)
README gains a "Run it" section: one app command
(python -m streamlit run src/dashboard/app.py) and one test command
(python -m pytest tests/), noting Streamlit Cloud deploys the same
entry point from requirements.txt, plus the canonical-data note.
Makefile rewritten cross-platform (PYTHON ?= python; no
.venv/Scripts/*.exe paths) and exercised end-to-end (make test).
Launcher removal is WAIVER-B and was not done.

## Verification (Batch 2)
- New tests: 29 (6 silent defaults + 3 evidence display + 6 hub
  health + 4 bootstrap CI + 4 WPA OOS + 3 canonical layer + 3
  player_of_match), all passing; 1 existing test updated (register
  status, above).
- Full suite in this worktree: 443 passed, 5 failed, 13 skipped —
  the 5 failures are exactly the Batch 1 known-baseline set
  (coach_shadow frozen-log pin, hardening manifest, provisional
  policy, registry mapping, hub lock-stage); 414 → 443 is precisely
  the 29 new tests. No new failures. (An intermediate run showed 6
  extra failures from the 1.2 sync — NRR path-dependence, register
  status, ingest dtype alignment — all diagnosed and fixed inside
  the sync/test layer as recorded under 1.2 above.)
- frozen_log.csv md5 unchanged (1bebae9831038ea9137f2fb1d2e0b0d4),
  verified before and after the batch. PREREGISTRATION_S3.md
  untouched. Main repo untouched by this batch.
