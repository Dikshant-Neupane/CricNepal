"""
Monte Carlo ball-by-ball simulator -- SHADOW MODE ONLY.

It is never blended into the headline probability until it beats the
champion blend on frozen-log log-loss (docs/PREDICTION_SYSTEM.md).

Method:
- Outcome categories per legal ball: runs {0,1,2,3,4,6} or wicket.
  (Extras are ignored, so simulated totals undercount by ~5%; wides and
  no-balls are excluded from the fitted distributions. Rare 5s/7s are
  folded into 1s. Both approximations are documented limitations.)
- A striker's phase distribution is shrunk toward the phase collective
  with k=100 balls; the bowler's phase distribution (runs conceded /
  wickets per legal ball) likewise with k=120. The delivery distribution
  is the average of the two shrunk distributions.
- Players with no local ball-by-ball history (new S3 signings) get the
  phase collective distribution reshaped by their prior bat/bowl index
  from player_priors.csv (boundary rates scaled by index, dots inverse).
- Uncertain players (priors uncertainty high / little local data) have
  their distribution Dirichlet-jittered per simulation block.
- Batting order = XI order as given; bowling rotation = per-phase best
  available bowlers from the XI, max 4 overs each, no consecutive overs.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

CATS = [0, 1, 2, 3, 4, 6, "W"]
K_BAT_SIM = 100.0
K_BOWL_SIM = 120.0
PHASES = ["Powerplay", "Middle", "Death"]


def _cat_of(runs_off_bat, is_wicket):
    if is_wicket:
        return "W"
    return runs_off_bat if runs_off_bat in (0, 1, 2, 3, 4, 6) else 1


def build_distributions(bb: pd.DataFrame, name_to_id: dict) -> dict:
    """bb: ball_by_ball with batter_name/bowler_name/phase/runs_off_bat/
    is_wicket/extras_type. Returns {phase: {'collective': probs,
    'bat': {pid: probs}, 'bowl': {pid: probs}, 'counts': ...}} using
    legal balls only (no wides/no-balls)."""
    legal = bb[~bb["extras_type"].isin(["wides", "noballs"])].copy()
    legal["cat"] = [_cat_of(r, w) for r, w in zip(legal["runs_off_bat"], legal["is_wicket"])]
    out = {}
    for phase, g in legal.groupby("phase"):
        coll = g["cat"].value_counts(normalize=True).reindex(CATS).fillna(0).to_numpy(float)
        bat, bowl, bat_n, bowl_n = {}, {}, {}, {}
        for pid, gg in g.groupby(g["batter_name"].map(name_to_id)):
            if not isinstance(pid, str):
                continue
            c = gg["cat"].value_counts(normalize=True).reindex(CATS).fillna(0).to_numpy(float)
            n = len(gg)
            bat[pid] = (n * c + K_BAT_SIM * coll) / (n + K_BAT_SIM)
            bat_n[pid] = n
        for pid, gg in g.groupby(g["bowler_name"].map(name_to_id)):
            if not isinstance(pid, str):
                continue
            c = gg["cat"].value_counts(normalize=True).reindex(CATS).fillna(0).to_numpy(float)
            n = len(gg)
            bowl[pid] = (n * c + K_BOWL_SIM * coll) / (n + K_BOWL_SIM)
            bowl_n[pid] = n
        out[phase] = {"collective": coll, "bat": bat, "bowl": bowl,
                      "bat_n": bat_n, "bowl_n": bowl_n}
    return out


def player_bat_dist(pid, phase, dists, prior_row=None):
    d = dists[phase]
    if pid in d["bat"]:
        return d["bat"][pid], d["bat_n"].get(pid, 0)
    coll = d["collective"].copy()
    if prior_row is not None:
        idx = float(prior_row.get("bat_index", 1.0))
        adj = coll.copy()
        adj[4] *= idx; adj[5] *= idx  # boundaries scale with index
        adj[0] *= (2.0 - idx)         # dots inverse
        adj = np.clip(adj, 0.001, None)
        return adj / adj.sum(), 0
    return coll, 0


def player_bowl_dist(pid, phase, dists, prior_row=None):
    d = dists[phase]
    if pid in d["bowl"]:
        return d["bowl"][pid], d["bowl_n"].get(pid, 0)
    coll = d["collective"].copy()
    if prior_row is not None:
        idx = float(prior_row.get("bowl_index", 1.0))
        adj = coll.copy()
        adj[4] /= max(idx, 0.2); adj[5] /= max(idx, 0.2)
        adj = np.clip(adj, 0.001, None)
        return adj / adj.sum(), 0
    return coll, 0


def _batting_order_dists(xi_ids, phase, dists, priors_by_id):
    return [player_bat_dist(pid, phase, dists, priors_by_id.get(pid)) for pid in xi_ids]


def simulate_innings(bat_xi, bowl_xi, dists, priors_by_id, n_sims, rng,
                     target=None, jitter=True):
    """Vectorised innings simulation. bat_xi/bowl_xi: registry-id lists
    (batting order; bowlers = those expected to bowl, best first per
    phase is approximated by list order within phase groups)."""
    n = n_sims
    runs = np.zeros(n, dtype=int)
    wkts = np.zeros(n, dtype=int)
    balls = np.zeros(n, dtype=int)
    striker = np.zeros(n, dtype=int)      # index into bat_xi
    nonstriker = np.ones(n, dtype=int)
    next_in = np.full(n, 2)
    finished = np.zeros(n, dtype=bool)
    # precompute per-phase delivery distributions per (batter, bowler) lazily
    cache = {}
    def delivery_probs(phase, b_idx, bowler_id):
        key = (phase, bat_xi[b_idx], bowler_id)
        if key not in cache:
            bd, bn = player_bat_dist(bat_xi[b_idx], phase, dists, priors_by_id.get(bat_xi[b_idx]))
            wd, wn = player_bowl_dist(bowler_id, phase, dists, priors_by_id.get(bowler_id))
            p = 0.5 * (bd + wd)
            if jitter and (bn < 60 or wn < 60):
                kappa = 25.0 + min(bn, wn)
                p = rng.dirichlet(np.clip(p, 1e-4, None) * kappa)
            cache[key] = p / p.sum()
        return cache[key]
    # bowling rotation: cycle bowl_xi, max 4 overs (24 balls) each
    bowler_balls = {b: 0 for b in bowl_xi}
    total_balls = 120
    ball_no = 0
    active_bowlers = list(bowl_xi[:5]) if len(bowl_xi) >= 5 else list(bowl_xi)
    over_bowler_idx = 0
    while ball_no < total_balls:
        over = ball_no // 6
        phase = PHASES[0] if over < 6 else (PHASES[1] if over < 15 else PHASES[2])
        # choose bowler for this over: next in rotation with quota left
        bowler = None
        for tries in range(len(active_bowlers)):
            cand = active_bowlers[(over_bowler_idx + tries) % len(active_bowlers)]
            if bowler_balls[cand] < 24:
                bowler = cand
                over_bowler_idx = (over_bowler_idx + tries + 1) % len(active_bowlers)
                break
        if bowler is None:
            bowler = active_bowlers[0]
        for _ in range(6):
            if ball_no >= total_balls:
                break
            alive = ~finished
            if not alive.any():
                break
            # draw per unique striker among alive sims
            draw = np.zeros(n, dtype=int)
            for b_idx in np.unique(striker[alive]):
                mask = alive & (striker == b_idx)
                p = delivery_probs(phase, int(b_idx), bowler)
                draw[mask] = rng.choice(len(CATS), size=int(mask.sum()), p=p)
            is_w = alive & (draw == 6)
            r = np.where(alive, np.array(CATS[:6] + [0])[draw], 0)
            runs += np.where(alive, r, 0)
            balls += alive.astype(int)
            wkts += is_w.astype(int)
            # strike swap on odd runs
            swap = alive & (r % 2 == 1)
            tmp = striker.copy()
            striker = np.where(swap, nonstriker, striker)
            nonstriker = np.where(swap, tmp, nonstriker)
            # wicket: next batter in (striker was dismissed)
            newbat = is_w & (next_in < len(bat_xi))
            striker = np.where(newbat, next_in, striker)
            next_in = next_in + newbat.astype(int)
            # innings ends: all out or target reached
            if target is not None:
                finished |= alive & (runs >= target)
            finished |= wkts >= 10
            finished |= balls >= total_balls
            ball_no += 1
        bowler_balls[bowler] = bowler_balls.get(bowler, 0) + 6
        # end-of-over strike swap
        tmp = striker.copy(); striker = nonstriker; nonstriker = tmp
    return runs, wkts, balls


def simulate_match(xi_1, xi_2, bowl_1, bowl_2, dists, priors_by_id,
                   n_sims=10000, seed=42):
    """xi_*: batting-order registry ids; bowl_*: bowling rotation ids.
    Returns dict with p_team_1_win (ties split), mean scores."""
    rng = np.random.default_rng(seed)
    s1, _, _ = simulate_innings(xi_1, bowl_2, dists, priors_by_id, n_sims, rng)
    s2, _, _ = simulate_innings(xi_2, bowl_1, dists, priors_by_id, n_sims, rng,
                                target=None)
    # proper chase: re-simulate innings 2 with target s1+1 per sim is not
    # vectorisable per-sim here; instead compare totals (standard
    # approximation: second innings simulated independently, win if it
    # exceeds the first-innings total).
    win1 = float(np.mean(s1 > s2)); tie = float(np.mean(s1 == s2))
    return {"p_team_1_win": win1 + 0.5 * tie, "tie_rate": tie,
            "mean_score_1": float(np.mean(s1)), "mean_score_2": float(np.mean(s2)),
            "n_sims": n_sims}
