import os
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(ROOT, "data")

def safe_read(path):
    if os.path.exists(path):
        return pd.read_csv(path)
    return None

def main():
    per_season_path = os.path.join(DATA_DIR, "per_bowler_season_features.csv")
    enriched_path = r"D:/cric_data/data/player_profiles/enriched_players_20260521.csv"

    df_season = safe_read(per_season_path)
    df_enriched = safe_read(enriched_path)

    if df_season is None:
        print(f"Missing {per_season_path}; make sure `prepare_season_features.py` ran.")
        return

    if df_enriched is None:
        print(f"Warning: enriched players file not found at {enriched_path}. Proceeding without profile merges.")

    # Normalize player name column
    df_season = df_season.rename(columns=lambda s: s.strip())
    if 'player_name' not in df_season.columns:
        # try common alternatives
        for c in ['bowler','bowler_name','player','name']:
            if c in df_season.columns:
                df_season = df_season.rename(columns={c:'player_name'})
                break

    if 'season_id' not in df_season.columns and 'season' in df_season.columns:
        df_season['season_id'] = df_season['season']

    # Keep seasons 1 and 2 only
    df = df_season.copy()
    df = df[df['season_id'].isin([1, '1', 2, '2', 'Season 1', 'Season 2', 'S1', 'S2'])]

    # Merge enriched profiles if available
    if df_enriched is not None:
        df_enriched = df_enriched.rename(columns=lambda s: s.strip())
        if 'player_name' not in df_enriched.columns:
            df_enriched = df_enriched.rename(columns={'player_name':'player_name'})
        df = df.merge(df_enriched[['player_name','primary_role','bowling_type','age']], on='player_name', how='left')

    # If overall economy not present, try to compute a weighted economy from phase econ + balls
    if 'economy' not in df.columns and 'powerplay_econ' in df.columns and 'powerplay_balls' in df.columns and 'death_econ' in df.columns and 'death_balls' in df.columns:
        def weighted_econ(row):
            try:
                pb = float(row.get('powerplay_balls', 0) or 0)
                db = float(row.get('death_balls', 0) or 0)
                total_b = pb + db
                if total_b <= 0:
                    return None
                pr = float(row.get('powerplay_econ', 0) or 0) * pb
                dr = float(row.get('death_econ', 0) or 0) * db
                # econ units are runs per over; convert using balls->overs factor
                # but since both are per-over rates, using balls weights is an approximation
                return (pr + dr) / total_b
            except Exception:
                return None
        df['economy'] = df.apply(weighted_econ, axis=1)

    # Select or compute core features
    feats = []
    if 'balls_bowled' in df.columns:
        df['overs_bowled'] = df['balls_bowled'] / 6.0
        feats.append('overs_bowled')
    if 'matches' in df.columns:
        feats.append('matches')
    if 'wickets' in df.columns:
        feats.append('wickets')
    if 'runs_conceded' in df.columns:
        feats.append('runs_conceded')
    if 'economy' in df.columns:
        feats.append('economy')

    # Add profile-derived features
    if 'age' in df.columns:
        feats.append('age')
    if 'bowling_type' in df.columns:
        # simple categorical encoding
        dummies = pd.get_dummies(df['bowling_type'].fillna('unknown'), prefix='bow_type')
        df = pd.concat([df, dummies], axis=1)
        feats += list(dummies.columns)
    if 'primary_role' in df.columns:
        role_d = pd.get_dummies(df['primary_role'].fillna('unknown'), prefix='role')
        df = pd.concat([df, role_d], axis=1)
        feats += list(role_d.columns)

    # Pivot S1 features and S2 target by player
    # We'll build rows for players who have season 1 and season 2 records
    # Normalize season_id to 1/2
    def norm_season(x):
        if pd.isna(x):
            return x
        s = str(x).strip().upper()
        if s.startswith('S') and len(s) <= 3:
            # S1, S2
            try:
                return int(s.replace('S',''))
            except Exception:
                return x
        if 'SEASON' in s:
            try:
                # 'Season 1' -> 1
                return int(s.split()[-1])
            except Exception:
                return x
        try:
            return int(s)
        except Exception:
            return x
    df['season_id_norm'] = df['season_id'].apply(norm_season)

    s1 = df[df['season_id_norm'] == 1]
    s2 = df[df['season_id_norm'] == 2]

    # set index
    s1 = s1.set_index('player_name')
    s2 = s2.set_index('player_name')

    common_players = list(set(s1.index).intersection(set(s2.index)))
    rows = []
    for p in common_players:
        row = {'player_name': p}
        for f in feats:
            v = s1.loc[p][f] if f in s1.columns else None
            # if multiple entries per season, take mean
            if isinstance(v, pd.Series):
                v = v.mean()
            row[f"s1_{f}"] = v
        # target: s2 economy if available
        target = s2.loc[p]['economy'] if 'economy' in s2.columns else None
        if isinstance(target, pd.Series):
            target = target.mean()
        row['s2_economy'] = target
        rows.append(row)

    out = pd.DataFrame(rows)
    out_path = os.path.join(DATA_DIR, 'extended_per_bowler_features.csv')
    out.to_csv(out_path, index=False)
    print(f"Wrote extended features to {out_path} — rows: {len(out)}")

if __name__ == '__main__':
    main()
