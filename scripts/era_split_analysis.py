"""
S2 Era-Split Analysis — Janakpur Bolts
=======================================
Priority #4: Identify tactical/captaincy shifts within S2.

Split S2 into two halves (early = first 16 matches, late = last 16 matches).
For Janakpur Bolts specifically, measure:
  - Team economy (conceded runs/over)
  - Wickets per match
  - Dot ball percentage
  - Bowling rotation entropy (Shannon entropy of overs distributed)
  - Win/loss record per half
  - Phase-specific economy (powerplay vs death)

Output:
  deliverables/janakpur_s2_era_analysis.md
  deliverables/janakpur_s2_era_bowlers.csv

Usage:
  python scripts/era_split_analysis.py
"""

import os
import math
import numpy as np
import pandas as pd

ROOT      = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR  = os.path.join(ROOT, "data")
DELIV     = os.path.join(ROOT, "deliverables")
os.makedirs(DELIV, exist_ok=True)

TEAM = "Janakpur Bolts"


def load_data():
    bbb_path     = os.path.join(DATA_DIR, "normalized", "ball_by_ball_normalized.parquet")
    matches_path = os.path.join(DATA_DIR, "normalized", "matches_normalized.parquet")
    bbb     = pd.read_parquet(bbb_path)
    matches = pd.read_parquet(matches_path)
    return bbb, matches


def split_s2_matches(matches: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (early_matches, late_matches) for S2, sorted by date."""
    s2 = matches[matches["season"] == "S2"].sort_values("match_date").reset_index(drop=True)
    mid = len(s2) // 2
    return s2.iloc[:mid].copy(), s2.iloc[mid:].copy()


def bowling_rotation_entropy(match_ids: list, bbb: pd.DataFrame) -> float:
    """
    Shannon entropy of overs distribution across Janakpur bowlers.
    Higher entropy = more rotation (deeper bowling attack); lower = over-reliance on 1–2 bowlers.
    """
    sub = bbb[(bbb["match_id"].isin(match_ids)) & (bbb["bowling_team"] == TEAM)]
    overs_per_bowler = sub.groupby(["bowler_name", "match_id", "over"]).size().reset_index()
    count = overs_per_bowler.groupby("bowler_name").size()
    probs = count / count.sum()
    entropy = -sum(p * math.log2(p) for p in probs if p > 0)
    return entropy


def phase_economy(match_ids: list, bbb: pd.DataFrame, phase: str) -> float:
    sub = bbb[
        (bbb["match_id"].isin(match_ids)) &
        (bbb["bowling_team"] == TEAM) &
        (bbb["phase"] == phase)
    ]
    if sub.empty:
        return np.nan
    balls = len(sub)
    runs  = sub["runs_total"].sum()
    return runs / (balls / 6) if balls > 0 else np.nan


def era_stats(era_label: str, m_ids: list, bbb: pd.DataFrame, matches: pd.DataFrame) -> dict:
    # bowling stats for Janakpur
    sub = bbb[(bbb["match_id"].isin(m_ids)) & (bbb["bowling_team"] == TEAM)]

    total_balls  = len(sub)
    total_runs   = sub["runs_total"].sum()
    total_wkts   = sub["is_wicket"].sum()
    total_dots   = sub["is_dot_ball"].sum()
    n_matches    = matches[matches["match_id"].isin(m_ids)]
    jan_matches  = n_matches[(n_matches["team_1_name"] == TEAM) | (n_matches["team_2_name"] == TEAM)]
    wins         = (jan_matches["winner_name"] == TEAM).sum()

    economy     = total_runs / (total_balls / 6) if total_balls > 0 else np.nan
    dot_pct     = total_dots / total_balls * 100 if total_balls > 0 else np.nan
    wkts_pm     = total_wkts / len(jan_matches) if len(jan_matches) > 0 else np.nan
    entropy     = bowling_rotation_entropy(m_ids, bbb)
    pp_econ     = phase_economy(m_ids, bbb, "Powerplay")
    death_econ  = phase_economy(m_ids, bbb, "Death")

    return {
        "era":           era_label,
        "matches":       len(jan_matches),
        "wins":          wins,
        "losses":        len(jan_matches) - wins,
        "win_pct":       wins / len(jan_matches) * 100 if len(jan_matches) > 0 else 0,
        "economy":       economy,
        "dot_ball_pct":  dot_pct,
        "wickets_pm":    wkts_pm,
        "pp_economy":    pp_econ,
        "death_economy": death_econ,
        "rotation_entropy": entropy,
        "total_balls":   total_balls,
    }


def top_bowlers_by_era(era_label: str, m_ids: list, bbb: pd.DataFrame) -> pd.DataFrame:
    sub = bbb[(bbb["match_id"].isin(m_ids)) & (bbb["bowling_team"] == TEAM)]
    g = sub.groupby("bowler_name").agg(
        balls        = ("runs_total", "count"),
        runs         = ("runs_total", "sum"),
        wickets      = ("is_wicket", "sum"),
        dot_balls    = ("is_dot_ball", "sum"),
    ).reset_index()
    g["economy"]   = g["runs"] / (g["balls"] / 6)
    g["dot_pct"]   = g["dot_balls"] / g["balls"] * 100
    g["overs"]     = g["balls"] / 6
    g["era"]       = era_label
    g = g[g["balls"] >= 6]  # min 1 over
    return g.sort_values("economy")


def detect_changes(early: dict, late: dict) -> list[str]:
    """Identify significant shifts between era halves."""
    changes = []

    econ_delta = late["economy"] - early["economy"]
    if abs(econ_delta) >= 0.5:
        direction = "worsened" if econ_delta > 0 else "improved"
        changes.append(f"Economy {direction} by {abs(econ_delta):.2f} runs/over "
                       f"({early['economy']:.2f} → {late['economy']:.2f})")

    dot_delta = late["dot_ball_pct"] - early["dot_ball_pct"]
    if abs(dot_delta) >= 3:
        direction = "decreased" if dot_delta < 0 else "increased"
        changes.append(f"Dot ball% {direction} by {abs(dot_delta):.1f}pp "
                       f"({early['dot_ball_pct']:.1f}% → {late['dot_ball_pct']:.1f}%)")

    ent_delta = late["rotation_entropy"] - early["rotation_entropy"]
    if abs(ent_delta) >= 0.3:
        direction = "deeper" if ent_delta > 0 else "narrower"
        changes.append(f"Bowling rotation became {direction} "
                       f"(entropy {early['rotation_entropy']:.2f} → {late['rotation_entropy']:.2f})")

    if early["wins"] != late["wins"]:
        changes.append(f"Win/loss: Early {early['wins']}W-{early['losses']}L, "
                       f"Late {late['wins']}W-{late['losses']}L")

    if not changes:
        changes.append("No major tactical shifts detected between early and late S2.")
    return changes


def generate_captaincy_signals(
    early: dict,
    late: dict,
    early_bowlers: pd.DataFrame,
    late_bowlers: pd.DataFrame,
) -> list[str]:
    """Infer captaincy/tactical decisions from data patterns."""
    signals = []

    # Over-reliance: if top 2 bowlers deliver >60% of overs in either era
    for era_label, eb in [("Early S2", early_bowlers), ("Late S2", late_bowlers)]:
        top2_overs = eb.nlargest(2, "overs")["overs"].sum()
        total_overs = eb["overs"].sum()
        share = top2_overs / total_overs * 100 if total_overs > 0 else 0
        if share > 60:
            top_names = ", ".join(eb.nlargest(2, "overs")["bowler_name"].tolist())
            signals.append(f"{era_label}: Top-2 bowlers ({top_names}) account for "
                           f"{share:.0f}% of overs — over-reliance detected.")

    # Death bowling vulnerability
    if not np.isnan(early["death_economy"]) and not np.isnan(late["death_economy"]):
        if late["death_economy"] - early["death_economy"] > 0.5:
            signals.append(f"Death economy deteriorated in late S2 "
                           f"({early['death_economy']:.2f} → {late['death_economy']:.2f}) — "
                           f"consider recruiting specialist death bowler for S3.")

    # Powerplay
    if not np.isnan(early["pp_economy"]) and not np.isnan(late["pp_economy"]):
        if late["pp_economy"] - early["pp_economy"] > 0.5:
            signals.append(f"Powerplay economy worsened in late S2 "
                           f"({early['pp_economy']:.2f} → {late['pp_economy']:.2f}) — "
                           f"new-ball bowling strategy needs review.")

    if not signals:
        signals.append("No clear captaincy/strategy issues detected from era comparison.")
    return signals


def write_report(
    early: dict,
    late: dict,
    early_bowlers: pd.DataFrame,
    late_bowlers: pd.DataFrame,
    changes: list,
    captaincy: list,
    out_path: str,
):
    lines = [
        f"# {TEAM} — S2 Era-Split Analysis",
        "",
        "Split: **Early S2** (matches 1–16) vs **Late S2** (matches 17–32)",
        "",
        "## Team Performance by Era",
        "",
        "| Metric | Early S2 | Late S2 | Δ |",
        "|---|---|---|---|",
    ]
    metrics = [
        ("Matches (with Janakpur)", "matches", "{:.0f}"),
        ("Win %", "win_pct", "{:.0f}%"),
        ("Economy (runs/over)", "economy", "{:.2f}"),
        ("Dot ball %", "dot_ball_pct", "{:.1f}%"),
        ("Wickets / match", "wickets_pm", "{:.2f}"),
        ("Powerplay economy", "pp_economy", "{:.2f}"),
        ("Death economy", "death_economy", "{:.2f}"),
        ("Rotation entropy (bits)", "rotation_entropy", "{:.2f}"),
    ]
    for label, key, fmt in metrics:
        ev = early[key]
        lv = late[key]
        if pd.isna(ev) or pd.isna(lv):
            delta = "—"
            ev_s  = "—"
            lv_s  = "—"
        else:
            delta = fmt.format(lv - ev) if isinstance(lv - ev, float) else f"{lv - ev}"
            ev_s  = fmt.format(ev)
            lv_s  = fmt.format(lv)
        lines.append(f"| {label} | {ev_s} | {lv_s} | {delta} |")

    lines += [
        "",
        "## Significant Shifts",
        "",
    ]
    for c in changes:
        lines.append(f"- {c}")

    lines += [
        "",
        "## Captaincy / Tactical Signals",
        "",
    ]
    for s in captaincy:
        lines.append(f"- {s}")

    lines += [
        "",
        "## Top Bowlers — Early S2",
        "",
        "| Bowler | Overs | Economy | Wickets | Dot% |",
        "|---|---|---|---|---|",
    ]
    for _, row in early_bowlers.head(8).iterrows():
        lines.append(
            f"| {row['bowler_name']} | {row['overs']:.1f} "
            f"| {row['economy']:.2f} | {int(row['wickets'])} | {row['dot_pct']:.1f}% |"
        )

    lines += [
        "",
        "## Top Bowlers — Late S2",
        "",
        "| Bowler | Overs | Economy | Wickets | Dot% |",
        "|---|---|---|---|---|",
    ]
    for _, row in late_bowlers.head(8).iterrows():
        lines.append(
            f"| {row['bowler_name']} | {row['overs']:.1f} "
            f"| {row['economy']:.2f} | {int(row['wickets'])} | {row['dot_pct']:.1f}% |"
        )

    lines += [
        "",
        "## S3 Recruitment Implications",
        "",
        "Based on the era-split, priority S3 needs for Janakpur:",
        "1. **Bowling depth** — if rotation entropy dropped late, need 1–2 additional"
        " specialist options to reduce over-reliance.",
        "2. **Phase specialisation** — if death economy worsened, recruit a proven"
        " yorker/death specialist.",
        "3. **Captain-proof bowling** — bowlers who maintain economy across all phases"
        " reduce dependence on tactical perfection.",
    ]

    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def main():
    print("Loading data...")
    bbb, matches = load_data()

    early_m, late_m = split_s2_matches(matches)
    early_ids = early_m["match_id"].tolist()
    late_ids  = late_m["match_id"].tolist()

    print(f"S2 early matches: {len(early_ids)}  late matches: {len(late_ids)}")

    early = era_stats("Early S2", early_ids, bbb, matches)
    late  = era_stats("Late S2",  late_ids,  bbb, matches)

    print(f"\nEarly S2 → Janakpur: {early['wins']}W-{early['losses']}L  econ={early['economy']:.2f}")
    print(f"Late  S2 → Janakpur: {late['wins']}W-{late['losses']}L  econ={late['economy']:.2f}")

    early_bowlers = top_bowlers_by_era("Early S2", early_ids, bbb)
    late_bowlers  = top_bowlers_by_era("Late S2",  late_ids,  bbb)

    changes   = detect_changes(early, late)
    captaincy = generate_captaincy_signals(early, late, early_bowlers, late_bowlers)

    print("\nKey changes:")
    for c in changes:
        print(f"  • {c}")
    print("\nCaptaincy signals:")
    for s in captaincy:
        print(f"  • {s}")

    # Save combined bowler CSV
    bowler_csv = pd.concat([early_bowlers, late_bowlers], ignore_index=True)
    csv_out = os.path.join(DELIV, "janakpur_s2_era_bowlers.csv")
    bowler_csv.to_csv(csv_out, index=False)
    print(f"\nBowler CSV → {csv_out}")

    md_out = os.path.join(DELIV, "janakpur_s2_era_analysis.md")
    write_report(early, late, early_bowlers, late_bowlers, changes, captaincy, md_out)
    print(f"Report → {md_out}")


if __name__ == "__main__":
    main()
