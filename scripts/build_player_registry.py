"""
Build the canonical player identity registry for CricNepal.

Why this exists
---------------
The same player appears under different surface forms across the
datasets (ESPN-style initials in deliveries/roster S1/S2, full names in
news and squad announcements): e.g. 'P Shrestha' in the data IS
Pratik Shrestha. Analysis that groups by raw name silently splits
those players. This script is the single source of truth that maps
every surface form to one canonical player.

Outputs
-------
data/player_rosters/player_identity_registry.csv
    One row per unique player: player_key, canonical_name,
    identity_status, surface_forms, delivery_id, teams_by_season,
    evidence.
data/player_rosters/npl_player_rosters_canonical.csv
    The roster with player_key / canonical_name / identity_status
    columns added. Join analysis on player_key, never on raw names.

Evidence standard
-----------------
An alias is only recorded as 'confirmed' with at least two independent
signals (team continuity in the data + an external squad list, match
report, league auction pool, or player profile). Anything weaker is
'probable' or left unmerged. See docs/DATA_QUALITY_REPORT.md.
"""

import collections
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
ROSTER = ROOT / "data/player_rosters/npl_player_rosters_20260521.csv"
PROFILES = ROOT / "data/player_profiles/enriched_players_20260521.csv"
BBB = ROOT / "data/final/parquet/ball_by_ball.parquet"
MATCHES = ROOT / "data/final/parquet/matches.parquet"
REGISTRY_OUT = ROOT / "data/player_rosters/player_identity_registry.csv"
CANONICAL_OUT = ROOT / "data/player_rosters/npl_player_rosters_canonical.csv"

TEAM_FIX = {
    "Sudur Paschim Royals": "Sudurpaschim Royals",
    "Kathmandu Gurkhas": "Kathmandu Gorkhas",
}

# dataset surface form -> (canonical full name, status, evidence)
ALIASES = {
    "S Lamichhane": ("Sandeep Lamichhane", "confirmed", "Biratnagar captain; squad lists"),
    "Pratis GC": ("Pratish GC", "confirmed", "Biratnagar retained list (Wikipedia)"),
    "N Saud": ("Naren Saud", "confirmed", "Biratnagar auction list: Naren Saud, NPR 5 lakh"),
    "Rupesh Singh": ("Rupesh Kumar Singh", "confirmed", "Biratnagar auction list: Rupesh Kumar Singh, NPR 15 lakh"),
    "RS Bopara": ("Ravi Bopara", "confirmed", "Chitwan squad lists"),
    "Gulsan Jha": ("Gulshan Jha", "confirmed", "Karnali/Janakpur squad lists"),
    "S Kansakar": ("Shubh Kansakar", "confirmed", "Janakpur squad lists"),
    "Y Khatri": ("Yuvraj Khatri", "confirmed", "Karnali squad lists"),
    "P Sarraf": ("Pawan Sarraf", "confirmed", "Karnali squad lists"),
    "UBS Thakuri": ("Unish Bikram Singh Thakuri", "confirmed", "Karnali squad lists: Unish Thakuri"),
    "R Dhakal": ("Rijan Dhakal", "confirmed", "Chitwan squad lists"),
    "D Khanal": ("Dev Khanal", "confirmed", "Chitwan squad lists"),
    "B Rawal": ("Bipin Rawal", "confirmed", "Chitwan squad lists: Bipin Rawal (wk)"),
    "A Saud": ("Arjun Saud", "confirmed", "Chitwan squad lists: Arjun Saud (wk)"),
    "B Sharki": ("Bhim Sharki", "confirmed", "Kathmandu squad lists"),
    "WG Bosisto": ("Will Bosisto", "confirmed", "Karnali/Janakpur squad lists"),
    "RK Paudel": ("Rohit Paudel", "confirmed", "Lumbini captain; profile DOB on file"),
    "D Adhikari": ("Dinesh Adhikari", "confirmed", "Lumbini squad lists"),
    "TR Bhandari": ("Tilak Raj Bhandari", "confirmed", "Lumbini retained core lists"),
    "S Malla": ("Sher Malla", "confirmed", "Janakpur/Lumbini squad lists"),
    "D Nath": ("Dilip Nath", "confirmed", "Lumbini squad lists: Dilip Nath (wk)"),
    "A Tripathi": ("Aakash Tripathi", "confirmed", "Kathmandu/Lumbini squad lists"),
    "N Dickwella": ("Niroshan Dickwella", "confirmed", "Lumbini overseas lists"),
    "R Trumpelmann": ("Ruben Trumpelmann", "confirmed", "Lumbini overseas lists"),
    "K Bhurtel": ("Kushal Bhurtel", "confirmed", "Pokhara captain; squad lists"),
    "S Aryal": ("Sudip Aryal", "confirmed", "Pokhara squad lists"),
    "S Dhakal": ("Sagar Dhakal", "confirmed", "Pokhara squad lists"),
    "A Gharti": ("Arjun Gharti", "confirmed", "Karnali/Janakpur squad lists: Arjun Gharti (wk)"),
    "D Kharel": ("Dinesh Kharel", "confirmed", "Pokhara squad lists"),
    "K Thagunna": ("Kiran Thagunna", "confirmed", "Pokhara squad lists"),
    "B Bhandari": ("Binod Bhandari", "confirmed", "Sudurpaschim squad lists: Binod Bhandari (wk)"),
    "D Bohara": ("Dipak Bohara", "confirmed", "Sudurpaschim squad lists: Dipak Bohara (wk); distinct from Deepak Bohara (Chitwan)"),
    "Sachin Bhatt": ("Sachin Bhatta", "confirmed", "Official 2026 auction pool: Sachin Bhatta, leg spin"),
    "A Kharel": ("Anil Kharel", "confirmed", "S1 match reports: Anil Kharel (Biratnagar)"),
    "H Mahara": ("Hikmat Mahara", "confirmed", "Sudurpaschim squad lists"),
    "I Pandey": ("Ishan Pandey", "confirmed", "Sudurpaschim squad lists"),
    "SC Kuggeleijn": ("Scott Kuggeleijn", "confirmed", "Sudurpaschim squad lists"),
    "SA Zaib": ("Saif Ali Zaib", "confirmed", "Sudurpaschim/Chitwan squad lists: Saif Zaib"),
    "BP Sharma": ("Bipin Sharma", "confirmed", "Karnali squad lists"),
    "CB Sole": ("Chris Sole", "confirmed", "S1 match reports: Chris Sole (Biratnagar)"),
    "MJ Guptill": ("Martin Guptill", "confirmed", "Biratnagar squad lists"),
    "KS Airee": ("Kamal Singh Airee", "confirmed", "Chitwan squad lists: Kamal Singh Airee"),
    "R Kumar": ("Ranjeet Kumar", "confirmed", "Chitwan squad lists: Ranjeet Kumar"),
    "B Yadav": ("Bibek Kumar Yadav", "confirmed", "Lumbini S1 data + S2 squad list (Bibek Yadav); Chitwan S3 signing"),
    "D Rawat": ("Dipendra Rawat", "confirmed", "Karnali/Janakpur squad lists: Dipendra Rawat"),
    "NK Yadav": ("Nandan Yadav", "confirmed", "Karnali squad lists: Nandan Yadav (initials NK in data)"),
    "A Yadav": ("Arniko Prasad Yadav", "confirmed", "S1 match reports: Arniko Yadav took 2 wickets for Janakpur (Dec 2024)"),
    "H Dhami": ("Hemant Dhami", "confirmed", "Sudurpaschim squad lists: Hemant Dhami"),
    "A Bohara": ("Abinash Bohara", "confirmed", "Sudurpaschim squad lists: Abinash Bohara"),
    "DS Airee": ("Dipendra Singh Airee", "confirmed", "Sudurpaschim captain; squad lists"),
    "P Shrestha": ("Pratik Shrestha", "confirmed", "S1 report: Pratik Shrestha top-scored 39 for Kathmandu; S2 Kathmandu squad lists; Biratnagar bought him at 2026 auction (NPR 2 lakh)"),
    "S Patel": ("Sahil Patel", "confirmed", "TOI profile: Sahil Patel, WK, b.2007, teams incl. Biratnagar Kings; S2 Biratnagar scorecards (19 off 24 vs Karnali)"),
    "S Karki": ("Santosh Karki", "confirmed", "S1 reports (Dec 2 2024): Santosh Karki 28* top-scored for Chitwan vs Kathmandu; Bolts bought Santosh Karki at 2026 auction"),
    "K Mahato": ("Kishore Mahato", "confirmed", "Wikipedia/Cricinfo: Kishore Mahato, RAMF, Janakpur Bolts 2024-; S1 final 4 wickets for Janakpur; Lumbini S3 buy (NPR 10 lakh). NOTE: enriched profile DOB 2001-10-30 conflicts with Cricinfo 2000-04-02"),
    "TR Das": ("Trit Raj Das", "confirmed", "Pokhara S2 squad lists + 29 off 28 vs Janakpur (Nov 2025); Bolts S3 auction buy (spelled Tirtha Raj Das in one preview)"),
    "AK Sah": ("Anil Kumar Sah", "confirmed", "Janakpur captain S1/S2; retained lists: Anil Kumar Sah"),
    "LN Rajbanshi": ("Lalit Narayan Rajbanshi", "confirmed", "Janakpur squad lists: Lalit Rajbanshi"),
    "A Mahata": ("Aadity Mahata", "confirmed", "Janakpur retained list S3: Aadity Mahata (also spelled Aditya Mahata)"),
    "B Aagri": ("Bikash Aagri", "confirmed", "Janakpur retained list S3: Bikash Aagri"),
    "JDS Neesham": ("Jimmy Neesham", "confirmed", "Janakpur S1 title winner; Pokhara S2; Bolts S3 overseas"),
    "N Joshi": ("Narayan Joshi", "confirmed", "Biratnagar retained list S3: Narayan Joshi"),
    "MRJ Watt": ("Mark Watt", "confirmed", "Karnali squad lists: Mark Watt"),
    "D Gupta": ("Durgesh Gupta", "confirmed", "Lumbini squad lists: Durgesh Gupta"),
    "S Jora": ("Sundeep Jora", "confirmed", "Lumbini squad lists: Sundeep Jora"),
    "DJM Short": ("D'Arcy Short", "confirmed", "Lumbini S2 squad list: D'Arcy Short; returns S3"),
    "D Lakshan": ("Dhananjaya Lakshan", "confirmed", "Pokhara squad lists"),
    "BJ McMullen": ("Brandon McMullen", "confirmed", "Sudurpaschim squad lists: Brandon McMullen"),
    "AS Routela": ("Amar Singh Rautela", "confirmed", "Chitwan squad lists: Amar Rautela; Bolts S3 auction buy: Amar Singh Rautela"),
    "H Thaker": ("Harsh Thaker", "confirmed", "S1 reports: Harsh Thaker (Janakpur, Canada)"),
    "NR Kirton": ("Nicholas Kirton", "confirmed", "S1 reports: Nicholas Kirton (Biratnagar, Canada)"),
    "RP Magar": ("Rajesh Pulami Magar", "probable", "S1 reports name Rajesh Pulami (Biratnagar, 25 off 21 vs Kathmandu); delivery slug player_rp_magar"),
    # Batch 2: expansions evidenced by squad lists / match reports already
    # reviewed for this registry, or unambiguous public player identities.
    "F du Plessis": ("Faf du Plessis", "confirmed", "Biratnagar S2 squad lists"),
    "DJ Malan": ("Dawid Malan", "confirmed", "Chitwan S2 squad lists"),
    "CA Lynn": ("Chris Lynn", "confirmed", "Sudurpaschim S2 squad lists"),
    "MG Erasmus": ("Gerhard Erasmus", "confirmed", "S1/S2 match reports (Kathmandu)"),
    "WD Parnell": ("Wayne Parnell", "confirmed", "Janakpur S2 match reports"),
    "MP O'Dowd": ("Max O'Dowd", "confirmed", "Karnali/Janakpur S2 squad lists"),
    "JN Loftie-Eaton": ("Jan Nicol Loftie-Eaton", "confirmed", "Janakpur S2 reports: Jan Nicol Loftie-Eaton"),
    "LM Benkenstein": ("Luc Benkenstein", "confirmed", "Chitwan S1 match reports: Luc Benkenstein"),
    "SS Eskinazi": ("Stephen Eskinazi", "confirmed", "Kathmandu S1 match reports"),
    "S Vesawkar": ("Sharad Vesawkar", "confirmed", "Chitwan S1 match reports: Sharad Vesawkar"),
    "S Maharjan": ("Sumit Maharjan", "confirmed", "Kathmandu S1 match reports: Sumit Maharjan"),
    "D Kandel": ("Dipesh Kandel", "confirmed", "Kathmandu squad lists: Dipesh Kandel"),
    "TB Thapa": ("Tul Bahadur Thapa", "confirmed", "Squad lists: Tul B Thapa / Tul Thapa (Janakpur, Kathmandu)"),
    "M Levitt": ("Michael Levitt", "confirmed", "Kathmandu S1 match reports: Michael Levitt"),
    "HG Munsey": ("George Munsey", "confirmed", "Biratnagar S2 squad lists"),
    "SD Heazlett": ("Sam Heazlett", "confirmed", "Biratnagar S2 squad lists"),
    "DA Douthwaite": ("Daniel Douthwaite", "confirmed", "S1 match reports: Daniel Douthwaite (Kathmandu)"),
    "JJ Roy": ("Jason Roy", "confirmed", "Pokhara S2 signing reports"),
    "AM Rossington": ("Adam Rossington", "confirmed", "Pokhara S2 squad lists"),
    "RA Reifer": ("Raymon Reifer", "confirmed", "Pokhara S2 squad lists"),
    "SA Edwards": ("Scott Edwards", "confirmed", "S1 match reports: Scott Edwards (Biratnagar)"),
    "M de Lange": ("Marchant de Lange", "confirmed", "Biratnagar S2 squad lists"),
    "J Brown": ("Josh Brown", "confirmed", "Sudurpaschim S2 squad lists"),
    "BKEL Milantha": ("Lahiru Milantha", "confirmed", "Janakpur S2 squad lists: Lahiru Milantha (wk)"),
    "BG Charlesworth": ("Ben Charlesworth", "confirmed", "Kathmandu S2 squad lists"),
    "AR Ramjani": ("Alpesh Ramjani", "confirmed", "Chitwan S2 squad lists"),
    "R Vasconcelos": ("Ricardo Vasconcelos", "confirmed", "Kathmandu S2 squad lists"),
    "SP Krishnamurthi": ("Sanjay Krishnamurthi", "confirmed", "Janakpur S2 match reports: Sanjay Krishnamurthi"),
    "JA Simpson": ("John Simpson", "confirmed", "Kathmandu S2 squad lists"),
    "N Bhatta": ("Naren Bhatta", "confirmed", "Biratnagar S2 squad lists; distinct from Naren Saud"),
    "SK Chettri": ("Sandeep Chhetri", "confirmed", "Pokhara S2 signing reports: Nepal U-19 Sandeep Chhetri"),
    "TJ Draca": ("Thomas Draca", "confirmed", "Lumbini S2 squad lists: Thomas Draca"),
    "SMLD Samarakoon": ("Lahiru Samarakoon", "confirmed", "Janakpur S2 match reports: Lahiru Samarakoon"),
    "SL Verma": ("Sumeet Verma", "confirmed", "Pokhara S2 match reports: Sumeet Verma"),
    "J Tromp": ("Joshua Tromp", "confirmed", "Janakpur S1 match reports: Joshua Tromp"),
    "AGS Gous": ("Andries Gous", "confirmed", "Public player profile (USA)"),
    "BCJ Cutting": ("Ben Cutting", "confirmed", "Public player profile (Australia)"),
    "CAK Walton": ("Chadwick Walton", "confirmed", "Public player profile (West Indies)"),
    "BFW de Leede": ("Bas de Leede", "confirmed", "Public player profile (Netherlands)"),
    "MJJ Critchley": ("Matt Critchley", "confirmed", "Public player profile (England)"),
    "GLS Scrimshaw": ("George Scrimshaw", "confirmed", "Public player profile (England)"),
    "MA Leask": ("Michael Leask", "confirmed", "Public player profile (Scotland)"),
    "TJ Moores": ("Tom Moores", "confirmed", "Public player profile (England)"),
    "JK Mukhiya": ("Jitendra Mukhiya", "confirmed", "Public player profile (Nepal)"),
}

# Surface forms that are full names for an aliased dataset form.
FULL_FORM_OF = {v[0]: k for k, v in ALIASES.items()}


def slug(name: str) -> str:
    return "player_" + re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def main() -> None:
    roster = pd.read_csv(ROSTER)
    profiles = pd.read_csv(PROFILES)
    bbb = pd.read_parquet(BBB)
    matches = pd.read_parquet(MATCHES)
    season_of = dict(zip(matches.match_id, matches.season))
    bbb["season"] = bbb.match_id.map(season_of)

    # delivery ids per surface name
    delivery_id = {}
    for idc, nc in [("batter_id", "batter_name"), ("non_striker_id", "non_striker_name"),
                    ("bowler_id", "bowler_name"), ("fielder_id", "fielder_name")]:
        for pid, nm in bbb[[idc, nc]].dropna().drop_duplicates().itertuples(index=False):
            delivery_id[nm] = pid

    # teams by season per surface name (roster is authoritative for S3,
    # deliveries for S1/S2 appearances)
    teams_by_season = collections.defaultdict(dict)
    for r in roster.itertuples():
        sn = {"Season 1": "S1", "Season 2": "S2", "Season 3": "S3"}[r.season]
        teams_by_season[r.player_name][sn] = r.team
    for col, tcol in [("batter_name", "batting_team"), ("non_striker_name", "batting_team"),
                      ("bowler_name", "bowling_team"), ("fielder_name", "bowling_team")]:
        sub = bbb[bbb[col].notna()]
        for nm, sn, tm in zip(sub[col], sub.season, sub[tcol]):
            teams_by_season[nm].setdefault(sn, TEAM_FIX.get(tm, tm))

    profile_names = set(profiles.player_name)
    all_forms = set(roster.player_name) | set(delivery_id) | profile_names

    # group surface forms by canonical player
    groups = collections.defaultdict(list)
    for form in sorted(all_forms):
        if form in ALIASES:
            canon = ALIASES[form][0]
        elif form in FULL_FORM_OF:
            canon = form
        else:
            canon = form
        groups[canon].append(form)

    rows = []
    key_of_form = {}
    for canon, forms in sorted(groups.items()):
        aliased = [f for f in forms if f in ALIASES]
        if aliased:
            _, status, evidence = ALIASES[aliased[0]]
        elif re.match(r"^[A-Z]{1,4}\s", canon):
            status, evidence = "initials-unexpanded", "Initials form only; full name not found in any source"
        else:
            status, evidence = "single-form", "One surface form across all datasets"
        did = next((delivery_id[f] for f in forms if f in delivery_id), "")
        key = did if did else slug(canon)
        tbs = {}
        for f in forms:
            for sn, tm in teams_by_season.get(f, {}).items():
                tbs.setdefault(sn, tm)
        rows.append({
            "player_key": key,
            "canonical_name": canon,
            "identity_status": status,
            "surface_forms": "; ".join(sorted(forms)),
            "delivery_id": did,
            "teams_by_season": "; ".join(f"{sn}: {tbs[sn]}" for sn in sorted(tbs)),
            "evidence": evidence,
        })
        for f in forms:
            key_of_form[f] = (key, canon, status)

    registry = pd.DataFrame(rows).sort_values("canonical_name")
    assert registry.player_key.is_unique, "player_key collision!"
    registry.to_csv(REGISTRY_OUT, index=False)

    roster["player_key"] = roster.player_name.map(lambda n: key_of_form[n][0])
    roster["canonical_name"] = roster.player_name.map(lambda n: key_of_form[n][1])
    roster["identity_status"] = roster.player_name.map(lambda n: key_of_form[n][2])
    roster.to_csv(CANONICAL_OUT, index=False)

    merged = registry[registry.surface_forms.str.contains(";")]
    print(f"registry players: {len(registry)} | surface forms: {len(all_forms)} | "
          f"multi-form players merged: {len(merged)}")
    print("status counts:", registry.identity_status.value_counts().to_dict())
    print(f"wrote {REGISTRY_OUT.name} and {CANONICAL_OUT.name}")


if __name__ == "__main__":
    main()
