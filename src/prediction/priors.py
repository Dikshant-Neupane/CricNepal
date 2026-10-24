"""
Cross-league T20 history aggregation + shrunk player priors.

Recipe (research report 2026-10-24, section 6):
- History = ALL cricsheet T20 competitions (NPL, T20 internationals, IPL,
  PSL, BBL, BPL, CPL, LPL, ILT20, SA20, MLC), last ~3 years, joined on the
  cricsheet registry ID (never name strings).
- Each ball is decay-weighted, half-life 18 months to the reference date.
- Cross-league translation acts on the DEVIATION from the source league's
  mean, shrunk by a per-league factor t (documented assumption, not tuned:
  overlap samples are too small for per-league estimation).
- Priors shrink toward the NPL league mean with k=150 balls faced (batting)
  / k=120 balls bowled (bowling): prior = mean + dev * n/(n+k).
- Players with no history anywhere receive the league-mean prior with the
  widest uncertainty (group 'debutant'); players whose history is entirely
  external receive group 'external_pro' and 1.5x uncertainty.
"""
from __future__ import annotations

import json
import zipfile
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

REF_DATE = date(2026, 10, 26)
CUTOFF = date(2023, 10, 26)  # ~3 years of history
HALF_LIFE_DAYS = 548.0
K_BAT = 150.0
K_BOWL = 120.0
BOWLER_WICKETS = {"bowled", "caught", "caught and bowled", "lbw", "stumped",
                  "hit wicket", "retired out"}

# zip name -> (competition label, translation factor t)
COMPETITIONS = {
    "npl_json.zip": ("NPL", 1.00),
    "t20s_json.zip": ("T20I", 0.90),
    "ipl_json.zip": ("IPL", 0.85),
    "psl_json.zip": ("PSL", 0.85),
    "bbl_json.zip": ("BBL", 0.85),
    "bpl_json.zip": ("BPL", 0.80),
    "cpl_json.zip": ("CPL", 0.80),
    "lpl_json.zip": ("LPL", 0.80),
    "ilt_json.zip": ("ILT20", 0.80),
    "sat_json.zip": ("SA20", 0.85),
    "mlc_json.zip": ("MLC", 0.80),
}
PHASES = ["Powerplay", "Middle", "Death"]


def _phase(over_idx: int) -> str:
    return "Powerplay" if over_idx <= 5 else ("Middle" if over_idx <= 14 else "Death")


def _decay(d: date, ref: date = REF_DATE) -> float:
    return 0.5 ** (max(0, (ref - d).days) / HALF_LIFE_DAYS)


def aggregate_cricsheet(zips: dict, ref_date: date = REF_DATE,
                        cutoff: date = CUTOFF) -> pd.DataFrame:
    """zips: {zip_path: competition_label}. Returns per-(registry_id,
    competition, phase) decay-weighted batting/bowling totals + an
    'ALL' phase row per competition."""
    recs = {}

    def add(pid, comp, phase, w, bat=None, bowl=None):
        if not pid:
            return
        key = (pid, comp, phase)
        r = recs.setdefault(key, dict(bat_balls=0.0, bat_runs=0.0, dismissals=0.0,
                                      bowl_balls=0.0, bowl_runs=0.0, bowl_wkts=0.0))
        if bat:
            r["bat_balls"] += w * bat[0]; r["bat_runs"] += w * bat[1]; r["dismissals"] += w * bat[2]
        if bowl:
            r["bowl_balls"] += w * bowl[0]; r["bowl_runs"] += w * bowl[1]; r["bowl_wkts"] += w * bowl[2]

    for zp, comp in zips.items():
        with zipfile.ZipFile(zp) as z:
            for name in z.namelist():
                if not name.endswith(".json"):
                    continue
                try:
                    d = json.loads(z.read(name))
                except Exception:
                    continue
                info = d.get("info", {})
                try:
                    mdate = date.fromisoformat(info["dates"][0])
                except Exception:
                    continue
                if mdate < cutoff or mdate >= ref_date:
                    continue
                people = info.get("registry", {}).get("people", {})
                w = _decay(mdate, ref_date)
                for inn in d.get("innings", []):
                    for over in inn.get("overs", []):
                        ph = _phase(int(over["over"]))
                        for dlv in over.get("deliveries", []):
                            extras = dlv.get("extras", {})
                            runs = dlv["runs"]
                            byes = extras.get("byes", 0); leg = extras.get("legbyes", 0)
                            wide = "wides" in extras; noball = "noballs" in extras
                            wkts = dlv.get("wickets", [])
                            dism = 1 if wkts else 0
                            bwkt = 1 if wkts and wkts[0].get("kind") in BOWLER_WICKETS else 0
                            batter_id = people.get(dlv["batter"])
                            bowler_id = people.get(dlv["bowler"])
                            bat = None if wide else (1, runs["batter"], dism)
                            bowl = None if (wide or noball) else (1, runs["total"] - byes - leg, bwkt)
                            for phase_key in (ph, "ALL"):
                                add(batter_id, comp, phase_key, w, bat=bat)
                                add(bowler_id, comp, phase_key, w, bowl=bowl)
    rows = [dict(registry_id=k[0], competition=k[1], phase=k[2], **v)
            for k, v in recs.items()]
    return pd.DataFrame(rows)


def league_means(agg: pd.DataFrame) -> pd.DataFrame:
    """Per (competition, phase): batting runs/ball, dismissal rate,
    bowling economy (runs/ball), from ALL players in that competition."""
    a = agg.copy()
    g = a.groupby(["competition", "phase"]).sum(numeric_only=True).reset_index()
    g["bat_rpb"] = g["bat_runs"] / g["bat_balls"].replace(0, np.nan)
    g["dism_rate"] = g["dismissals"] / g["bat_balls"].replace(0, np.nan)
    g["bowl_rpb"] = g["bowl_runs"] / g["bowl_balls"].replace(0, np.nan)
    return g


def _combine(agg_p: pd.DataFrame, means: pd.DataFrame, phase: str,
             kind: str, t_map: dict):
    """Weighted translated deviation + effective n for one player/phase."""
    sub = agg_p[agg_p["phase"] == phase]
    if not len(sub):
        return 0.0, 0.0
    m = means[means["phase"] == phase].set_index("competition")
    dev_num, n_tot = 0.0, 0.0
    for _, r in sub.iterrows():
        if r["competition"] not in m.index:
            continue
        t = t_map.get(r["competition"], 0.8)
        if kind == "bat":
            n = r["bat_balls"]
            if n <= 0:
                continue
            dev = t * (r["bat_runs"] / n - m.loc[r["competition"], "bat_rpb"])
        else:
            n = r["bowl_balls"]
            if n <= 0:
                continue
            # positive dev = concedes FEWER runs than league mean (better)
            dev = t * (m.loc[r["competition"], "bowl_rpb"] - r["bowl_runs"] / n)
        dev_num += n * dev
        n_tot += n
    return (dev_num / n_tot if n_tot else 0.0), n_tot


def compute_priors(agg: pd.DataFrame, master: pd.DataFrame) -> pd.DataFrame:
    means = league_means(agg)
    npl = means[(means["competition"] == "NPL")]
    if not len(npl):  # as-of dates before the first NPL season: reference
        # = ball-weighted mean across all available competitions
        npl = means.groupby("phase").apply(
            lambda g: pd.Series({
                "bat_rpb": float((g["bat_rpb"] * g["bat_balls"]).sum() / g["bat_balls"].sum()),
                "dism_rate": float((g["dism_rate"] * g["bat_balls"]).sum() / g["bat_balls"].sum()),
                "bowl_rpb": float((g["bowl_rpb"] * g["bowl_balls"]).sum() / g["bowl_balls"].sum()),
            }), include_groups=False).reset_index()
    npl_all = npl[npl["phase"] == "ALL"].iloc[0]
    t_map = {label: t for label, t in COMPETITIONS.values()}
    by_player = {pid: g for pid, g in agg.groupby("registry_id")}
    rows = []
    for _, mp in master.iterrows():
        pid = mp["cricsheet_registry_id"]
        pa = by_player.get(pid, pd.DataFrame(columns=agg.columns)) if isinstance(pid, str) else pd.DataFrame(columns=agg.columns)
        comps = sorted(pa["competition"].unique()) if len(pa) else []
        npl_balls = 0.0
        if len(pa):
            allrows = pa[pa["phase"] == "ALL"]
            npl_balls = float(allrows[allrows["competition"] == "NPL"]["bat_balls"].sum()
                              + allrows[allrows["competition"] == "NPL"]["bowl_balls"].sum())
        row = {"player_key": mp["player_key"], "canonical_name": mp["canonical_name"],
               "team": mp["team"], "role": mp["role"],
               "cricsheet_registry_id": pid,
               "history_competitions": ";".join(comps)}
        dev_bat, n_bat = _combine(pa, means, "ALL", "bat", t_map)
        dev_bowl, n_bowl = _combine(pa, means, "ALL", "bowl", t_map)
        shrink_bat = n_bat / (n_bat + K_BAT) if n_bat else 0.0
        shrink_bowl = n_bowl / (n_bowl + K_BOWL) if n_bowl else 0.0
        row["bat_balls_eff"] = round(n_bat, 1)
        row["bowl_balls_eff"] = round(n_bowl, 1)
        row["prior_bat_rpb"] = round(float(npl_all["bat_rpb"] + dev_bat * shrink_bat), 4)
        row["prior_bowl_econ"] = round(float(6 * (npl_all["bowl_rpb"] - dev_bowl * shrink_bowl)), 3)
        # batting index used by the model: runs/ball relative to league mean
        row["bat_index"] = round(row["prior_bat_rpb"] / float(npl_all["bat_rpb"]), 4)
        row["bowl_index"] = round(float(npl_all["bowl_rpb"] * 6) / row["prior_bowl_econ"], 4) if row["prior_bowl_econ"] else 1.0
        for ph in PHASES:
            d_b, n_b = _combine(pa, means, ph, "bat", t_map)
            d_w, n_w = _combine(pa, means, ph, "bowl", t_map)
            pm = npl[npl["phase"] == ph]
            if len(pm):
                pm = pm.iloc[0]
                row[f"prior_bat_rpb_{ph.lower()}"] = round(float(pm["bat_rpb"] + d_b * (n_b / (n_b + K_BAT) if n_b else 0)), 4)
                row[f"prior_bowl_econ_{ph.lower()}"] = round(float(6 * (pm["bowl_rpb"] - d_w * (n_w / (n_w + K_BOWL) if n_w else 0))), 3)
            row[f"bat_balls_eff_{ph.lower()}"] = round(n_b, 1)
            row[f"bowl_balls_eff_{ph.lower()}"] = round(n_w, 1)
        if n_bat + n_bowl == 0:
            group = "debutant"
        elif npl_balls == 0:
            group = "external_pro"
        else:
            group = "npl_experienced"
        row["prior_group"] = group
        base_unc = 1.0 / np.sqrt(1.0 + (n_bat + n_bowl) / 150.0)
        row["uncertainty"] = round(float(base_unc * (1.5 if group in ("external_pro", "debutant") else 1.0)), 4)
        rows.append(row)
    return pd.DataFrame(rows)
