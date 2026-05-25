import pandas as pd
import numpy as np
import joblib
from pathlib import Path

def train(features_csv='data/per_bowler_season_features.csv', model_out='models/s1_to_s2_model.joblib', report_out='deliverables/prediction_report.txt'):
    df = pd.read_csv(features_csv)
    # handle season labels like 'S1','S2' or numeric
    s1_label = 'S1' if 'S1' in df['season'].unique() else 1
    s2_label = 'S2' if 'S2' in df['season'].unique() else 2
    s1 = df[df['season'] == s1_label].set_index('bowler')
    s2 = df[df['season'] == s2_label].set_index('bowler')
    common = s1.index.intersection(s2.index)
    if len(common) < 10:
        print('Warning: small dataset for training:', len(common))
    X = []
    y_pp = []
    y_death = []
    for b in common:
        row1 = s1.loc[b]
        row2 = s2.loc[b]
        feat = [row1.get('powerplay_econ',0), row1.get('powerplay_dot_pct',0), row1.get('powerplay_balls',0), row1.get('death_econ',0), row1.get('death_dot_pct',0), row1.get('death_balls',0)]
        X.append(feat)
        y_pp.append(row2.get('powerplay_econ', np.nan))
        y_death.append(row2.get('death_econ', np.nan))
    X = np.array(X)
    y_pp = np.array(y_pp)
    y_death = np.array(y_death)
    if X.size == 0:
        raise RuntimeError('No training samples found (no common bowlers between S1 and S2)')

    # simple model: Ridge regression
    try:
        from sklearn.linear_model import Ridge
        from sklearn.model_selection import cross_val_score
    except Exception as e:
        raise RuntimeError('scikit-learn required: pip install scikit-learn')

    model_pp = Ridge(alpha=1.0)
    model_death = Ridge(alpha=1.0)
    model_pp.fit(X, y_pp)
    model_death.fit(X, y_death)

    Path('models').mkdir(exist_ok=True)
    joblib.dump({'pp': model_pp, 'death': model_death}, model_out)

    # cross-validated scores
    cv_pp = cross_val_score(model_pp, X, y_pp, scoring='neg_mean_squared_error', cv=5)
    cv_death = cross_val_score(model_death, X, y_death, scoring='neg_mean_squared_error', cv=5)

    with open(report_out, 'w') as f:
        f.write('Training report\n')
        f.write(f'n_samples: {len(common)}\n')
        f.write(f'CV MSE PP: {-cv_pp.mean():.4f} (std {cv_pp.std():.4f})\n')
        f.write(f'CV MSE Death: {-cv_death.mean():.4f} (std {cv_death.std():.4f})\n')
    print('Trained models and wrote report to', report_out)


if __name__ == '__main__':
    train()
