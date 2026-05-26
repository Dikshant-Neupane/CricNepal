import os
import pandas as pd
import joblib
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(ROOT, 'data')
MODELS_DIR = os.path.join(ROOT, 'models')
DELIVERABLES = os.path.join(ROOT, 'deliverables')

model_path = os.path.join(MODELS_DIR, 's1_to_s2_lgbm.joblib')
feat_path = os.path.join(DATA_DIR, 'extended_per_bowler_features.csv')
per_season = os.path.join(DATA_DIR, 'per_bowler_season_features.csv')

def main():
    if not os.path.exists(model_path):
        print('Model not found:', model_path)
        return
    if not os.path.exists(feat_path):
        print('Extended features missing:', feat_path)
        return
    if not os.path.exists(per_season):
        print('Per-season data missing:', per_season)
        return

    model = joblib.load(model_path)
    feats = list(pd.read_csv(feat_path).columns)
    X_cols = [c for c in feats if c.startswith('s1_')]

    ps = pd.read_csv(per_season)
    # map bowler -> player_name
    if 'player_name' not in ps.columns and 'bowler' in ps.columns:
        ps = ps.rename(columns={'bowler':'player_name'})

    # compute overs if balls columns exist
    if 'balls_bowled' in ps.columns:
        ps['overs_bowled'] = ps['balls_bowled'] / 6.0
    if 'powerplay_balls' in ps.columns:
        ps['powerplay_balls'] = ps['powerplay_balls']

    # normalize season id for S2
    def norm_season(x):
        try:
            s = str(x).strip()
            if s.upper().startswith('S'):
                return int(s.upper().replace('S',''))
            return int(s)
        except Exception:
            return x
    if 'season_id' not in ps.columns and 'season' in ps.columns:
        ps['season_id'] = ps['season']
    ps['season_id_norm'] = ps['season_id'].apply(norm_season)
    s2 = ps[ps['season_id_norm'] == 2].set_index('player_name')

    preds = []
    for player in s2.index.unique():
        row = s2.loc[player]
        if isinstance(row, pd.DataFrame):
            row = row.mean()
        feat_vals = {}
        for col in X_cols:
            orig = col.replace('s1_','')
            if orig in row.index:
                feat_vals[col] = row[orig]
            else:
                # common fallbacks
                if orig == 'overs_bowled' and 'powerplay_balls' in row.index and 'death_balls' in row.index:
                    feat_vals[col] = (float(row.get('powerplay_balls',0)) + float(row.get('death_balls',0)))/6.0
                else:
                    feat_vals[col] = 0.0
        Xs2 = pd.DataFrame([feat_vals]).fillna(0.0)
        pred = model.predict(Xs2)[0]
        preds.append({'player_name': player, 'pred_s3_economy': float(pred)})

    out = pd.DataFrame(preds).sort_values('pred_s3_economy')
    out_path = os.path.join(DELIVERABLES, 's3_bowler_predictions_lgbm.csv')
    out.to_csv(out_path, index=False)
    print('Wrote', out_path)

if __name__ == '__main__':
    main()
