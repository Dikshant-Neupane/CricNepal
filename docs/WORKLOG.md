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


---

# Batch 3 (2026-10-29, branch corrections/2026-10-29, WAIVER-A/B items, branch-only)

Built in the isolated worktree under Dikshant's continuation order.
Nothing merged to main; nothing committed; the main repo was not
edited (its only dirty files remain the known regenerated exports +
predictions_status.json from in-season jobs). frozen_log.csv md5
verified unchanged before and after (1bebae9831038ea9137f2fb1d2e0b0d4);
PREREGISTRATION_S3.md untouched. Suite baseline in this worktree
(Batch 2): 443 passed / 5 known failures / 13 skipped.

## 3.1 Overseas-cap enforcement (E2, E3) — WAIVER-A

Understand: docs/PLAYING_CONDITIONS.md records the max-4-overseas XI
rule as REPORTED-CORROBORATED (CAN officials, multiple outlets).
engine.select_expected_xi imposed no cap (its docstring said so);
scripts/lock_matchday.py validate_xi imposed none (same statement in
data/matchday/README.md and docs/PREDICTION_SYSTEM.md).

Tests first (tests/test_overseas_cap.py, 6 tests, all failed pre-fix):
a synthetic 13-man squad whose unconstrained top 11 holds 6 overseas
must be repaired to 4 (lowest-scored overseas out, best domestic in);
a squad frame missing is_overseas must be REFUSED (ValueError), and
unknown (NaN) flags must be refused — the cap may never be silently
skipped; real-data XIs pinned in tests/pinned_expected_xi_prefix.json
(pre-fix selector output on branch priors): already-legal teams must
come back byte-identical, violators minimally repaired
(overseas-out/domestic-in only, exactly excess-many swaps);
validate_xi rejects a 5-overseas announced XI with the reason and
returns a legal XI unchanged.

Implemented: engine.MAX_OVERSEAS_PER_XI = 4; the selector gains a
cap repair ahead of the existing WK/bowling repairs, preferring a
swap that keeps WK and bowling constraints satisfied (repair loop
bounded at 200 passes); validate_xi checks the count via the master
and raises with count + rule + source doc. Stale no-cap statements
updated in lock_matchday's docstring, data/matchday/README.md and
docs/PREDICTION_SYSTEM.md.

Corrected expected XIs on branch priors (overseas before → after):
- Janakpur Bolts 6 → 4: OUT Jimmy Neesham, Moeen Ali;
  IN Aashutosh Pandey, Bishal Susling.
- Chitwan Rhinos 5 → 4: OUT Dawid Malan; IN Bibek Kumar Yadav.
- Sudurpaschim Royals 5 → 4: OUT Brandon McMullen; IN Dipak Bohara.
- Biratnagar (3), Karnali (3), Lumbini (3), Kathmandu (4), Pokhara
  (4): unchanged, byte-identical (pinned test).

MERGE IMPACT (WAIVER-A): if merged mid-season, every future
prediction/lock computed from expected XIs prices the three
corrected XIs above instead of the illegal ones — Janakpur's
expected XI loses its two highest-profile overseas all-rounders, so
its XI-strength diffs (and P1_preseason probabilities for unplayed
fixtures) move; announced-XI locks (P1_post_XI) are unaffected in
composition but an announced XI with 5+ overseas would now be
REJECTED at validation instead of locked. Frozen log rows already
appended never change.

## 4.1 Registry-ID drop fix (D5, V1) — WAIVER-A

Understand: engine.predict_fixture mapped the XI through
reg_ids()/priors_by_id and silently DROPPED players without a
cricsheet registry ID, shrinking the xi_strength denominator —
contradicting model.xi_strength's documented by-key contract.

Audit-figure check (hand-recomputation before coding): the audit's
full-mean Biratnagar figure (bat 1.0274) reproduces EXACTLY on the
branch's priors/expected XI. The audit's dropped figure (1.0430)
could NOT be reproduced — not from current priors, not from the
current expected XIs, not from the locked upcoming_predictions.csv
XIs: no current XI (expected or locked) contains a no-ID player, so
old and new code give identical strengths for all 8 teams today
(verified per team post-fix: every delta 0.0000, dropped = 0). The
1.0430 figure is recorded here as NOT REPRODUCED; it presumably came
from an earlier XI/priors state. The defect is real but LATENT.

Tests (tests/test_xi_strength_contract.py): a synthetic XI with one
no-ID player (bat 0.90 among ten 1.20s) must score the full mean
(1.1727-based diff), not the dropped mean — failed pre-fix, passes
post-fix; plus the Biratnagar 1.0274 real-data regression.

Implemented: predict_fixture passes the full selected XI and
priors_by_key straight to xi_strength; the reg-id mapping block is
deleted.

MERGE IMPACT (WAIVER-A): no current number changes (proven above).
The change bites the first time an announced XI contains a no-ID
player (23 such players sit in the master squads): that lock's XI
strength would previously have been computed over 10 men; after a
merge it is computed over the real 11.

## 2.3 match_nrr all-out rule (C5)

Understand: model.match_nrr used stored overs for all-out innings
(its docstring admitted the approximation), feeding
engine.team_form_state's EWMA form feature and the backtest's
form_nrr_diff. src/cricket/metrics.adjusted_balls is the authority.

Tests (tests/test_match_nrr.py): hand example A 100 all out off 15.0
vs B 101/5 off 19.0 → −0.3158 (pre-fix +1.3509, failed first);
not-all-out and missing-wickets-column behaviour pinned unchanged;
real-data conformance vs delivery-derived NRR on the
CONF-003-consistent subset: 18 of 64 matches have both innings'
stored balls equal to the derived legal balls; all 36 team values
match to 1e-9 post-fix. (The other 46 matches carry at least one
stored-summary discrepancy — that is CONF-003's stored data, not
this formula; the stored overs stay factual and the adjustment is
the consumer-side rule.)

Implemented: match_nrr delegates the adjustment to
metrics.adjusted_balls (wickets columns read when present; legacy
rows without them keep actual-overs behaviour). The local
float-notation overs_to_balls stays (metrics' namesake parses
scorecard strings — different signature, listed under 2.5).

Measured changes in the branch: 96 of 128 team-match per-match NRR
values change (any match with an all-out innings moves both teams'
values; max |Δ| = 1.7815). Final EWMA form state per team
(before → after): Biratnagar −0.2186 → −0.6720 (−0.4535);
Chitwan −0.6170 → −0.7498; Janakpur −0.1671 → −0.1874;
Karnali −0.2878 → −0.3695; Kathmandu +0.4221 → +0.4139;
Lumbini +1.5586 → +1.6974; Pokhara −0.1562 → −0.1611;
Sudurpaschim −1.0491 → −0.6578 (+0.3914).

Backtest consequence (forced, see below): champion_blend metrics
IDENTICAL (log loss 0.689088, Brier 0.248003 — the champion does not
consume the form feature); the challenger's raw S2 backtest moves:
log loss 0.795869 → 0.812776, Brier 0.294020 → 0.303326,
accuracy 0.406 → 0.344 (n = 32) — the corrected NRR makes the
CHALLENGER's form feature slightly worse on S2. Reported, not
spun: the correction is right on the rules; the challenger was
already not beating the champion.

MERGE IMPACT (WAIVER-A): if merged mid-season, form features in
every subsequent prediction use the corrected NRR (largest shifts
Biratnagar/Sudurpaschim above), and the challenger artefact
regenerates with refit coefficients (below). Locked frozen-log rows
never change; already-published probabilities are not restated.

## 2.2 Priors BOWLER_WICKETS (C3) — with 6.2's columns

Understand: priors.BOWLER_WICKETS included "retired out", which
Section 4 / src/cricket/metrics.py does not credit to the bowler.
Tracing the data first: the aggregated bowl_wkts is written to
player_history.csv but compute_priors never consumes it (priors are
built from runs and balls only) — so the expected priors diff was
zero, and the rebuild confirmed exactly that (below).

Tests (tests/test_priors_batch3.py): synthetic cricsheet zip — one
bowled + one retired-out dismissal by the same bowler must aggregate
to exactly one wicket's decay weight (failed pre-fix: it counted
two); BOWLER_WICKETS must equal the metrics authority set;
compute_priors must carry is_overseas through and append the 6.2
interval columns LAST, bracketing the estimates, narrower for the
larger sample.

Implemented: BOWLER_WICKETS = set(metrics.BOWLER_CREDITED_WICKETS).
Rebuilt priors IN THE BRANCH (scripts/build_player_priors.py):
150 players, player set identical to the pre-rebuild file (no
drift pulled in — the feared main-branch drift did not materialise
because the build's inputs live in the scratch zips and the branch's
own master). Diff: player_history.csv — bowl_wkts changes on 131
(player, competition, phase) rows, total −89.19 decay-weighted
wickets (the retired-out credits removed); no other history column
changes. player_priors.csv — ZERO value changes on shared columns;
only the appended columns below differ.

## 6.2 Priors posterior interval (S1) — WAIVER-A

Added to compute_priors, appended at the very end of every row
(column order last five: is_overseas, bat_rpb_ci_lo, bat_rpb_ci_hi,
bowl_econ_ci_lo, bowl_econ_ci_hi): the documented normal
partial-pooling interval matching the shrinkage form — sd =
sqrt(mu/(n+k)) per ball (mu = league mean, k = K_BAT 150 / K_BOWL
120), economy sd × 6, ±1.96 sd, clipped at 0; n = 0 yields the
prior-only (widest) width. The heuristic `uncertainty` column is
kept unchanged.

Consumer check (grep the prediction path): every consumer reads the
priors by column NAME (engine.load_context, lock scripts, dashboard
loaders, tests) — none positionally. One real break found and fixed
during verification: scripts/backtest_prediction.py builds a
SYNTHETIC master from cricsheet lineups (no is_overseas — NPL
overseas status is undefined there) and crashed on the new column.
Contract now explicit: compute_priors emits NaN (= unknown, never a
guessed boolean) when the master lacks the column, and
select_expected_xi REFUSES missing or non-boolean flags (two tests
pin both refusals). Production masters always carry real booleans
(rebuilt file: 45 overseas True, matching the master).

MERGE IMPACT (WAIVER-A): player_priors.csv gains five columns; no
existing value changes, so no displayed or locked number changes.
The is_overseas column is what makes 3.1's enforcement possible at
predict time.


## 3.3 Remaining sourced validators (E3)

Squad validation report: src/prediction/squad_validation.py
validate_squads() encodes ONLY the sourced squad rule — 6–8 overseas
per squad (PLAYING_CONDITIONS.md) — as a per-team report wired into
scripts/build_player_master.py (writes
data/predictions/squad_validation_report.csv — a gitignored build
artefact — and prints flags; it NEVER fails the build: squads evolve
in-season). The Associate-presence clause is reported as NOT CHECKED
(Associate status per nationality is not sourced in-repo); total
squad size is info-only (no sourced limit). The master rebuild
reproduces player_master.csv identically, and the report flags 4 of
8 squads at 5 overseas on the branch snapshot (Biratnagar, Lumbini,
Pokhara, Sudurpaschim) — below the reported registration range,
recorded as flags for human review, exactly the report's purpose.
Impact/substitute and tie-break rules: NOT VERIFIED, NOT encoded.

Simulator constraints: the rotation block in
simulator.simulate_innings was extracted, behaviour-identically, to
simulator._choose_bowler (round-robin from a pointer, skip bowlers
at the 24-ball quota; pointer advances past the chosen bowler, so no
consecutive overs while ≥2 bowlers hold quota; all-at-quota falls
back to the first active bowler with the pointer unchanged — the
latent corner where fewer than 5 bowling options must cover 120
balls, e.g. 4 × 24 = 96 < 120). Tests
(tests/test_simulator_constraints.py) pin rotation order, quota
skip, no-consecutive over 20 overs, the fallback, and a seeded
end-to-end regression. A/B proof: the pre-extraction simulator (git
checkout) and the refactored one return BIT-IDENTICAL results on
pinned inputs (Biratnagar v Janakpur pre-fix XIs, n_sims = 500,
seed = 3: p 0.46, tie 0.016, means 135.298 / 139.928). Note: a
scratch capture taken during recon (p 0.532) used unrecorded inputs
and could not be reproduced; it is superseded by this A/B pair and
is NOT used as evidence.

MERGE IMPACT: none on numbers (master identical; simulator outputs
bit-identical). The only new behaviour is a printed/written squad
validation report at master-build time.

## 5.4 Challenger disclosure (V1, V5) — display variant only

The Match Predictions analysis now carries the oriented challenger
value per fixture (from upcoming_predictions.p_logistic_challenger)
and renders it with challenger_disclosure(): the disclosure text
reads trained_on from data/predictions/model_v1.json at runtime
(never hardcoded) and states the challenger is a shadow series that
did not beat the champion. Tests
(tests/test_challenger_disclosure.py): disclosure reads a synthetic
artefact verbatim, missing artefact → no line, all 28 real fixtures
carry correctly oriented values. The 5.4 change itself did NOT
modify the artefact (md5 da356cb4d1c5d1bc3469ed18267f6c0e verified
before and after this step).

Artefact regeneration (forced by 2.3, recorded here for honesty):
the pre-existing test test_g2c_backtest_features_truncation_invariance
recomputes backtest features from code and compares them with the
stored backtest_s2.csv; once match_nrr was corrected, the stored
artefacts had to be regenerated by their own pipeline
(scripts/backtest_prediction.py, then scripts/audit_simulator.py
for the additive bootstrap fields) or the branch would ship a
code/artefact inconsistency. Regeneration changed ONLY: challenger
scaler/coef/intercept in model_v1.json (new md5
52451c372230838acdc6d5a4c1779e8b), challenger + Platt rows in
backtest_metrics.json, and the challenger/feature columns of
backtest_s2.csv. trained_on ("S1+S2 (64 matches, tie excluded)"),
the chase block, the champion block, champion_blend metrics, both
bootstrap fields and simulator_audit.json are all identical to the
committed versions (diffed field by field).

MERGE IMPACT: if merged mid-season, the production challenger
artefact on main is replaced by the refit — future P1 challenger
probabilities shift slightly (the S2 backtest says the refit is
marginally worse; it remains a shadow series). Champion
probabilities are unaffected by the artefact itself; they move only
through 2.3's form feature and 3.1's XIs at predict time.

## 6.3 Opposition plan generator (S2, S3) — WAIVER-B (module only)

New module src/prediction/opposition_plan.py:
generate_opposition_plan(opponent, priors, approach=None,
head_to_head=None) — the opponent is an INPUT. Bowling and batting
entries per phase are built from that opponent's top phase subjects
in the priors table plus Janakpur's cap-legal expected XI, each
entry in the evidence structure (observation → evidence with n,
league baseline, interval → limitation → action → alternative);
team-level entries from the approach profile and head-to-head when
supplied. Discipline enforced by construction and by test
(tests/test_opposition_plan.py): evidence labels Limited (<30
balls) / Moderate (30–120) / Strong (>120); Limited entries carry
only the no-change action; a banned-content scan rejects line,
length, delivery-type and weakness vocabulary anywhere in the
output (the scan caught this module's own first-draft limitation
text, which NAMED the banned terms while disclaiming them — the
text was rewritten, the scan kept); no causal phrasing (actions are
options). Two opponents (Biratnagar, Lumbini) produce materially
different plans — on first run their ACTION lists were identical
(all intervals overlapped baselines and the generic text matched),
so the overlap-branch actions now cite the opponent's own estimate,
making the differentiation real rather than asserted.

Census on current priors (7 opponents × 6 phase entries): all 42
entries Strong at squad-aggregate level; 36 no-change (intervals
overlap baselines), 5 prioritise, 1 preserve. The honest headline:
on S1/S2 evidence, most phase matchups show no edge beyond noise —
the generator says so instead of inventing plans.

NOT done, deliberately: the frozen opposition page
(src/dashboard/page_modules/opposition_report.py) is untouched and
still reads its static forecast table. Rewiring it to this generator
is a merge-time WAIVER-B decision for Dikshant, not taken here.

MERGE IMPACT: none unless the page is rewired — the module is
additive and has no caller in the dashboard.

## Task 9 — CONF-002 / CONF-003 ingest fixes (D4, D6)

Future ingest behaviour only; no stored canonical row was patched
by this batch (the register entries stay open for stored data).
- CONF-003: scripts/ingest_cricsheet.py parse_match counted EVERY
  delivery row into the stored overs (wides and no-balls included).
  It now counts legal balls only ("wides"/"noballs" absent), the
  convention normalize's backfill already used. Synthetic test: 6
  legal + 1 wide + 1 no-ball stores 1.0 overs (not 1.2), runs and
  wickets unchanged, all 8 delivery rows preserved.
- CONF-002: normalize_team_names unified names but never IDs.
  TEAM_ID_MAPPING is now DERIVED from TEAM_NAME_MAPPING
  (team_kathmandu_gurkhas → team_kathmandu_gorkhas;
  team_sudur_paschim_royals → team_sudurpaschim_royals) and applied
  to team *_id columns only (a venue_id control value is untouched
  in the test). parse_match already stores team_1_id/team_2_id as
  None, so the split IDs are legacy residue; future normalization
  runs can no longer re-split them.
Tests: tests/test_ingest_fixes.py (3, both fixes failed pre-fix).

MERGE IMPACT: only future ingests/normalizations change — the first
post-merge cricsheet ingest stores legal-ball overs, and the next
normalization emits one Kathmandu team ID. Stored S1/S2 rows keep
their current (registered-conflict) values.

## 2.5 Dead-code removal (C6, safe subset)

Removed: _nrr_from_bbb (src/dashboard/page_modules/
executive_overview.py). Proof of death: exactly one occurrence in
the whole repo (excluding .git/__pycache__) — its own definition;
its docstring self-declared "legacy function - kept for reference";
and its arithmetic counted every delivery row as a ball (the
CONF-003 error). The file compiles and the dashboard import tests
pass in the full suite.

Listed, NOT removed (with reasons):
- model.overs_to_balls (float notation, 19.5 → 117) vs
  metrics.overs_to_balls (scorecard strings): different signatures
  and input domains; merging them is a refactor, not dead code.
- src/prediction/metrics.py (evaluation math: log loss, Brier, ECE)
  vs src/cricket/metrics.py (cricket arithmetic): a name collision
  across different domains, both live.
- src/dashboard/services/metrics.py KPI functions: consumed by
  frozen dashboard pages; removal is a product decision.
- ingest_cricsheet.phase_for vs metrics phase helpers: the ingest
  script sits outside the package import graph by design (scripts
  run standalone); deduplicating changes the ops surface.

## Verification (Batch 3)

- New tests: 35 across 9 files (priors 3, overseas cap 6, XI
  contract 2, match_nrr 4, squad validation 3, simulator 5,
  challenger disclosure 4, opposition plan 5, ingest fixes 3), all
  passing.
- Full suite in this worktree: 478 passed, 5 failed, 13 skipped —
  the 5 failures are exactly the Batch 1/2 known-baseline set
  (test_coach_shadow frozen-log pin, test_hardening_h1_h5 manifest,
  test_provisional_policy production-file, test_review_response_g
  registry mapping, test_season3_hub lock-stage); 443 → 478 is
  precisely the 35 new tests. One intermediate state failed
  test_g2c (stored backtest vs corrected code) — resolved by the
  pipeline regeneration recorded under 5.4, not by touching the
  test.
- frozen_log.csv md5 unchanged (1bebae9831038ea9137f2fb1d2e0b0d4),
  verified before and after. PREREGISTRATION_S3.md untouched.
  Main repo untouched by this batch.
- NOT VERIFIED in this batch: the playing-conditions handbook
  (still unpublished — the cap rests on REPORTED-CORROBORATED
  sourcing); Associate-nation status per player; impact/substitute
  and tie-break rules; the audit's 1.0430 dropped-mean figure
  (NOT REPRODUCED, see 4.1).
