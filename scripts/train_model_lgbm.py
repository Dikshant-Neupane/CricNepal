import os
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import KFold, RandomizedSearchCV
from sklearn.metrics import mean_squared_error
from lightgbm import LGBMRegressor

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(ROOT, "data")
MODELS_DIR = os.path.join(ROOT, "models")
DELIVERABLES = os.path.join(ROOT, "deliverables")

os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(DELIVERABLES, exist_ok=True)

def main():
    features_path = os.path.join(DATA_DIR, 'extended_per_bowler_features.csv')
    if not os.path.exists(features_path):
        print(f"Features file missing: {features_path}. Run `prepare_features_extended.py` first.")
        return

    df = pd.read_csv(features_path)
    df = df.dropna(subset=['s2_economy'])
    if df.shape[0] < 10:
        print(f"Warning: small sample size ({df.shape[0]}). Results will be noisy.")

    X_cols = [c for c in df.columns if c.startswith('s1_')]
    X = df[X_cols].fillna(0.0)
    y = df['s2_economy'].values

    # simple CV
    n_splits = min(5, max(2, df.shape[0] // 5))
    kf = KFold(n_splits=n_splits, shuffle=True, random_state=42)

    model = LGBMRegressor(random_state=42)

    param_dist = {
        'n_estimators': [50,100,200,400],
        'learning_rate': [0.01,0.05,0.1,0.2],
        'num_leaves': [7,15,31,63],
        'max_depth': [-1,3,5,8],
        'min_child_samples': [5,10,20,50],
        'reg_alpha': [0.0,0.1,0.5,1.0],
        'reg_lambda': [0.0,0.1,0.5,1.0]
    }

    rs = RandomizedSearchCV(model, param_distributions=param_dist, n_iter=20, cv=kf, scoring='neg_mean_squared_error', random_state=42, n_jobs=1)
    rs.fit(X, y)

    best = rs.best_estimator_
    print("Best params:", rs.best_params_)

    # cross-validated MSE on folds (manual)
    mses = []
    for train_idx, test_idx in kf.split(X):
        best.fit(X.iloc[train_idx], y[train_idx])
        preds = best.predict(X.iloc[test_idx])
        mses.append(mean_squared_error(y[test_idx], preds))
    mean_mse = float(np.mean(mses))

    # save model
    model_path = os.path.join(MODELS_DIR, 's1_to_s2_lgbm.joblib')
    joblib.dump(best, model_path)

    # save report
    report_path = os.path.join(DELIVERABLES, 'prediction_report_lgbm.txt')
    with open(report_path, 'w') as fh:
        fh.write(f"n_samples: {df.shape[0]}\n")
        fh.write(f"best_params: {rs.best_params_}\n")
        fh.write(f"cv_mse_mean: {mean_mse}\n")

    print(f"Saved model to {model_path}")
    print(f"Report written to {report_path}")

    # Apply model to S2 features to predict S3 (approx):
    # We will read original per-season features and build S2 feature rows
    per_season = os.path.join(DATA_DIR, 'per_bowler_season_features.csv')
    if os.path.exists(per_season):
        ps = pd.read_csv(per_season)
        # normalize names
        if 'player_name' not in ps.columns:
            for c in ['bowler_name','player','name']:
                if c in ps.columns:
                    ps = ps.rename(columns={c:'player_name'})
                    break
        # identify S2 rows
        if 'season_id' not in ps.columns and 'season' in ps.columns:
            ps['season_id'] = ps['season']
        def norm_season(x):
            try:
                return int(str(x).strip().split()[-1])
            except Exception:
                return x
        ps['season_id_norm'] = ps['season_id'].apply(norm_season)
        s2_rows = ps[ps['season_id_norm'] == 2].set_index('player_name')

        preds = []
        for player in df['player_name']:
            if player in s2_rows.index:
                # construct s2 feature vector with same columns as X (s1_* naming)
                row = s2_rows.loc[player]
                feat_vals = {}
                for col in X_cols:
                    orig = col.replace('s1_','')
                    val = None
                    if orig in row.index:
                        val = row[orig]
                    else:
                        # fallback to 0
                        val = 0.0
                    feat_vals[col] = val
                Xs2 = pd.DataFrame([feat_vals]).fillna(0.0)
                pred = best.predict(Xs2)[0]
            else:
                pred = np.nan
            preds.append({'player_name': player, 'pred_s3_economy': pred})
        out_pred = pd.DataFrame(preds)
        out_path = os.path.join(DELIVERABLES, 's3_bowler_predictions_lgbm.csv')
        out_pred.to_csv(out_path, index=False)
        print(f"Wrote predictions to {out_path}")

if __name__ == '__main__':
    main()
