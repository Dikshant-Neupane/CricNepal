"""
Player master file: one row per Season 3 squad player (133).

Built ONLY from sourced fields; anything unsourced is null and named in
`missing_fields`. Joins never use raw name strings across files:
- roster (canonical) provides player_key / canonical_name / role / team.
- enriched profiles join through the identity registry's surface forms
  (every one of the 188 profile rows is keyed by a registry surface form).
- cricsheet registry IDs join by exact name match against a registry map
  built from cricsheet downloads (canonical name, then surface forms).
Role comes from the S3 roster row (playing_role), NOT from the enriched
profiles' primary_role (which is 'Batter' for all 188 rows and is ignored).
"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pandas as pd

BOWLING_ARM = {}  # profiles carry type only (Spin/Medium Pace/Pace), no arm


def build_registry_map(zip_paths) -> dict:
    """name -> cricsheet registry ID, from info.registry.people of matches."""
    out = {}
    for zp in zip_paths:
        with zipfile.ZipFile(zp) as z:
            for name in z.namelist():
                if not name.endswith(".json"):
                    continue
                try:
                    d = json.loads(z.read(name))
                except Exception:
                    continue
                for pname, pid in d.get("info", {}).get("registry", {}).get("people", {}).items():
                    out.setdefault(pname, pid)
    return out


def _surface_to_key(registry: pd.DataFrame) -> dict:
    m = {}
    for _, r in registry.iterrows():
        forms = [x.strip() for x in str(r["surface_forms"]).replace(";", ",").split(",")]
        for f in forms:
            if f:
                m[f] = r["player_key"]
        m[str(r["canonical_name"])] = r["player_key"]
    return m


def build_player_master(root: Path, registry_map: dict | None = None) -> pd.DataFrame:
    root = Path(root)
    roster = pd.read_csv(root / "data/player_rosters/npl_player_rosters_canonical.csv")
    registry = pd.read_csv(root / "data/player_rosters/player_identity_registry.csv")
    profiles = pd.read_csv(root / "data/player_profiles/enriched_players_20260521.csv")
    s3 = roster[roster["season"] == "Season 3"].copy()

    surf2key = _surface_to_key(registry)
    prof_by_key = {}
    for _, p in profiles.iterrows():
        k = surf2key.get(str(p["player_name"]))
        if k:
            prof_by_key[k] = p
    reg_by_key = registry.set_index("player_key").to_dict("index")
    registry_map = registry_map or {}

    rows = []
    for _, r in s3.iterrows():
        key = r["player_key"]
        reg = reg_by_key.get(key, {})
        forms = [x.strip() for x in str(reg.get("surface_forms", "")).replace(";", ",").split(",") if x.strip()]
        candidates = [r["canonical_name"], r["player_name"]] + forms
        reg_id, reg_id_name = None, None
        for c in candidates:
            if c in registry_map:
                reg_id, reg_id_name = registry_map[c], c
                break
        match_type = "exact" if reg_id else None
        if reg_id is None and registry_map:
            # Constrained fallback for cricsheet initials forms (MM Ali,
            # AD Russell): surname equal, given part initials-only, first
            # initial equals canonical first initial, and GLOBALLY UNIQUE.
            import re as _re
            toks = str(r["canonical_name"]).split()
            if len(toks) >= 2:
                surname, first_init = toks[-1], toks[0][0].upper()
                cands = [n for n in registry_map
                         if n.split()[-1] == surname
                         and _re.fullmatch(r"[A-Z]{1,5}", n.split()[0])
                         and n.split()[0][0].upper() == first_init]
                if len(cands) == 1:
                    reg_id, reg_id_name = registry_map[cands[0]], cands[0]
                    match_type = "initials_surname_unique"
        p = prof_by_key.get(key)
        country = None if p is None or pd.isna(p["country"]) else str(p["country"])
        bat_hand = None
        bowling_type = None
        dob = None
        if p is not None:
            if not pd.isna(p["batting_hand"]) and p["batting_hand"] != "Unknown":
                bat_hand = str(p["batting_hand"])
            if not pd.isna(p["bowling_type"]):
                bowling_type = str(p["bowling_type"])
            if not pd.isna(p["date_of_birth"]):
                dob = str(p["date_of_birth"])
        age = None
        if dob:
            import datetime as _dt
            born = _dt.date.fromisoformat(dob[:10])
            ref = _dt.date(2026, 10, 26)
            age = round((ref - born).days / 365.25, 1)
        overseas = None
        if country:
            overseas = country not in ("Nepal",)
        missing = []
        if reg_id is None:
            missing.append("cricsheet_registry_id")
        if bat_hand is None:
            missing.append("batting_hand")
        if bowling_type is None:
            missing.append("bowling_type")
        if dob is None:
            missing.append("date_of_birth")
        if country is None:
            missing.append("nationality")
        rows.append({
            "player_key": key,
            "canonical_name": r["canonical_name"],
            "cricsheet_registry_id": reg_id,
            "registry_id_matched_name": reg_id_name,
            "registry_id_match_type": match_type,
            "team": r["team"],
            "role": r["playing_role"],
            "role_source": "s3_roster.playing_role",
            "batting_hand": bat_hand,
            "bowling_type": bowling_type,
            "bowling_arm": None,  # no in-repo source separates arm from type
            "date_of_birth": dob,
            "age_at_season_start": age,
            "nationality": country,
            "is_overseas": overseas,
            "identity_status": r["identity_status"],
            "missing_fields": ";".join(missing),
        })
    return pd.DataFrame(rows).sort_values(["team", "canonical_name"]).reset_index(drop=True)
