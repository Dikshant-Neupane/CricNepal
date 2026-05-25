import pandas as pd
import joblib

def predict(features_csv='data/per_bowler_season_features.csv', model_path='models/s1_to_s2_model.joblib', out_csv='deliverables/s3_bowler_predictions.csv'):
    df = pd.read_csv(features_csv)
    # determine S2 label
    s2_label = 'S2' if 'S2' in df['season'].unique() else 2
    s2 = df[df['season'] == s2_label].set_index('bowler')
    # load model
    mdl = joblib.load(model_path)
    model_pp = mdl['pp']
    model_death = mdl['death']

    rows = []
    for b, row in s2.iterrows():
        feat = [row.get('powerplay_econ',0), row.get('powerplay_dot_pct',0), row.get('powerplay_balls',0), row.get('death_econ',0), row.get('death_dot_pct',0), row.get('death_balls',0)]
        X = [feat]
        pp_pred = model_pp.predict(X)[0]
        death_pred = model_death.predict(X)[0]
        rows.append({'bowler': b, 'pp_econ_pred': pp_pred, 'death_econ_pred': death_pred, 'pp_econ_s2': row.get('powerplay_econ'), 'death_econ_s2': row.get('death_econ')})

    out = pd.DataFrame(rows).sort_values('death_econ_pred')
    out.to_csv(out_csv, index=False)
    print('Wrote S3 predictions to', out_csv)


if __name__ == '__main__':
    predict()
