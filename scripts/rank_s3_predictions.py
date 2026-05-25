import pandas as pd

def rank(input_csv='deliverables/s3_bowler_predictions.csv', out_md='deliverables/s3_predictions_ranked.md', top=10):
    df = pd.read_csv(input_csv)
    df['composite_pred'] = 0.5 * df['pp_econ_pred'] + 0.5 * df['death_econ_pred']
    df = df.sort_values('composite_pred')
    topn = df.head(top)
    with open(out_md, 'w', encoding='utf-8') as f:
        f.write('# S3 Predicted Best Bowlers (Top {})\n\n'.format(top))
        f.write('Based on S1->S2 learned model applied to S2 features. Lower composite = better.\n\n')
        for i, r in enumerate(topn.itertuples(), 1):
            f.write(f"{i}. {r.bowler}\n")
            f.write(f"   - PP econ pred: {r.pp_econ_pred:.2f}, Death econ pred: {r.death_econ_pred:.2f}, Composite: {r.composite_pred:.2f}\n")
            f.write(f"   - S2 observed: PP econ {r.pp_econ_s2}, Death econ {r.death_econ_s2}\n\n")
    print('Wrote ranked predictions to', out_md)

if __name__ == '__main__':
    rank()
