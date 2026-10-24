#!/usr/bin/env python
"""Simulator-advantage audit + headline uncertainty (review fixes R3/R4).

The Season 2 backtest reported log-loss: champion blend 0.6891, Elo
0.6888, shadow simulator 0.655. This audit asks whether the simulator's
advantage is established:

(a) Identical-set check — simulator backtest, champion backtest and the
    Elo baseline must be scored on the SAME match IDs.
(b) Leakage checklist — every simulator-backtest input traced, each
    item PASS or FLAG with evidence.
(c) Uncertainty — paired bootstrap over matches (10,000 resamples,
    fixed seed) of per-match log-loss differences (simulator-champion,
    simulator-Elo) and accuracy differences.
(d) Pre-committed verdict rule: if the 95% CI for simulator-champion
    log-loss difference includes 0, the verdict is
    "advantage not established".

R4: the same machinery gives champion-Elo log-loss difference with CI.

Outputs: data/predictions/simulator_audit.json, and additive bootstrap
fields in data/predictions/backtest_metrics.json (existing keys are
never modified).
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.prediction import metrics as MT  # noqa: E402

PRED = ROOT / "data" / "predictions"
SEED = 42
N_RESAMPLES = 10000


def compare_match_sets(named_sets: dict) -> dict:
    """Compare named match-ID sets: sizes, common intersection, and the
    symmetric differences between every pair. `identical` is True only
    if all sets are exactly equal."""
    names = list(named_sets)
    sets = {k: set(v) for k, v in named_sets.items()}
    inter = set.intersection(*sets.values()) if sets else set()
    pair_diffs = {}
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            pair_diffs[f"{a} vs {b}"] = {
                "only_in_first": sorted(sets[a] - sets[b]),
                "only_in_second": sorted(sets[b] - sets[a])}
    return {"sizes": {k: len(v) for k, v in sets.items()},
            "intersection_size": len(inter),
            "pair_differences": pair_diffs,
            "identical": all(not d["only_in_first"] and not d["only_in_second"]
                             for d in pair_diffs.values())}


def leakage_checklist() -> list:
    """Trace the simulator backtest's inputs. Source-inspection checks
    are programmatic where the artefact allows; items that cannot be
    proven from artefacts are FLAGged, not assumed."""
    sim_src = (ROOT / "src/prediction/simulator.py").read_text()
    bt_src = (ROOT / "scripts/backtest_simulator.py").read_text()
    items = []
    items.append({
        "item": "Outcome distributions fitted on Season 1 only",
        "status": "PASS" if "bb[bb.match_id.isin(s1_ids)]" in bt_src
        and "build_distributions" in bt_src else "FLAG",
        "evidence": "scripts/backtest_simulator.py builds distributions "
                    "from bb[bb.match_id.isin(s1_ids)] (S1 match IDs only) "
                    "before simulating any S2 match."})
    items.append({
        "item": "Player priors computed as of before Season 2",
        "status": "PASS" if "_priors_asof(date(2025, 11, 17)" in bt_src else "FLAG",
        "evidence": "backtest_simulator.py uses BT._priors_asof(2025-11-17) "
                    "-- the S2 start -- so no S2 delivery is inside a prior."})
    items.append({
        "item": "Playing XIs are the ACTUAL Season 2 XIs (post-hoc)",
        "status": "FLAG",
        "evidence": "XIs come from data/final/parquet/match_lineups.parquet "
                    "-- the XIs that actually played, knowable only at the "
                    "toss. The live P1 is also post-XI-announcement, so the "
                    "deployment task is comparable, but the backtest cannot "
                    "capture announcement-time uncertainty (late changes, "
                    "players who were announced but did not play)."})
    items.append({
        "item": "Simulator constants chosen without using Season 2 results",
        "status": "FLAG",
        "evidence": "K_BAT_SIM=100, K_BOWL_SIM=120 (src/prediction/"
                    "simulator.py), phase definitions (Powerplay/Middle/"
                    "Death from the data's phase column) and n_sims=2000 "
                    "are fixed in code, but there is NO pre-registered "
                    "record of when they were set relative to the S2 "
                    "backtest, so tuning-against-S2 cannot be ruled out "
                    "from the artefacts alone."})
    items.append({
        "item": "Monte Carlo noise in p_sim",
        "status": "FLAG",
        "evidence": "Backtest used 2,000 sims/match: Monte Carlo standard "
                    "error on a win probability is ~sqrt(0.25/2000) = "
                    "0.011 per match. The paired bootstrap treats p_sim "
                    "as fixed, so true uncertainty is slightly wider "
                    "than the reported CIs."})
    items.append({
        "item": "Outcome (y) is the target, never an input",
        "status": "PASS",
        "evidence": "y is derived from matches.winner_name after "
                    "simulation; no outcome field is read by "
                    "build_distributions or simulate_match."})
    return items


def main():
    core = pd.read_csv(PRED / "backtest_s2.csv")          # champion + Elo
    sim = pd.read_csv(PRED / "backtest_simulator.csv")    # simulator
    matches = pd.read_parquet(ROOT / "data/normalized/matches_normalized.parquet")
    s2_ids = set(matches[matches["season"] == "S2"]["match_id"])

    sets = compare_match_sets({
        "simulator_backtest": list(sim["match_id"]),
        "champion_backtest": list(core["match_id"]),
        "elo_baseline": list(core["match_id"]),  # Elo is a column of the champion backtest
        "season_2_matches": sorted(s2_ids)})
    assert sets["identical"], f"backtests are NOT on identical match sets: {sets}"

    m = sim.set_index("match_id").join(
        core.set_index("match_id")[["p_blend", "p_elo"]], how="inner")
    assert (m["y"] == (m.index.map(
        core.set_index("match_id")["y"]))).all(), "outcome mismatch between backtests"
    y = m["y"].to_numpy(float)

    def ll_boot(pa, pb):
        return MT.paired_bootstrap(MT.per_match_log_loss(pa, y)
                                   - MT.per_match_log_loss(pb, y),
                                   n_resamples=N_RESAMPLES, seed=SEED,
                                   lower_is_better=True)

    def acc_boot(pa, pb):
        return MT.paired_bootstrap(MT.per_match_correct(pa, y)
                                   - MT.per_match_correct(pb, y),
                                   n_resamples=N_RESAMPLES, seed=SEED,
                                   lower_is_better=False)

    boots = {
        "simulator_minus_champion_logloss": ll_boot(m["p_sim_team_1"], m["p_blend"]),
        "simulator_minus_elo_logloss": ll_boot(m["p_sim_team_1"], m["p_elo"]),
        "simulator_minus_champion_accuracy": acc_boot(m["p_sim_team_1"], m["p_blend"]),
        "simulator_minus_elo_accuracy": acc_boot(m["p_sim_team_1"], m["p_elo"]),
    }
    # R4: headline uncertainty, champion vs Elo
    champ_elo = MT.paired_bootstrap(
        MT.per_match_log_loss(m["p_blend"], y) - MT.per_match_log_loss(m["p_elo"], y),
        n_resamples=N_RESAMPLES, seed=SEED, lower_is_better=True)

    ci = boots["simulator_minus_champion_logloss"]
    verdict = ("advantage not established" if ci["ci_includes_zero"]
               else "advantage established on this backtest (still requires "
                    "frozen-log confirmation before promotion)")
    out = {
        "question": "Is the simulator's Season 2 backtest advantage over the "
                    "champion blend / Elo real?",
        "identical_set_check": sets,
        "leakage_checklist": leakage_checklist(),
        "bootstrap": boots,
        "champion_minus_elo_logloss": champ_elo,
        "verdict_rule": "Pre-committed: if the 95% CI for the simulator - "
                        "champion per-match log-loss difference includes 0, "
                        "the verdict is 'advantage not established'.",
        "verdict": verdict,
        "promotion_rule_unchanged": "The simulator stays in shadow mode; "
                                     "promotion requires beating the champion "
                                     "on the Season 3 frozen log, not on this "
                                     "backtest.",
    }
    (PRED / "simulator_audit.json").write_text(json.dumps(out, indent=1))

    # R4: additive fields only in backtest_metrics.json
    bm_path = PRED / "backtest_metrics.json"
    bm = json.loads(bm_path.read_text())
    bm["champion_vs_elo_bootstrap"] = champ_elo
    bm["simulator_vs_champion_bootstrap"] = boots["simulator_minus_champion_logloss"]
    bm_path.write_text(json.dumps(bm, indent=1))

    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
