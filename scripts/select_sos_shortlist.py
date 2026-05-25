import pandas as pd


def select(input_csv='deliverables/s3_bowler_shortlist_sos.csv', out_md='deliverables/s3_ceo_shortlist_sos_filtered.md', top=5, pp_min=60, death_min=30):
    df = pd.read_csv(input_csv)
    # require reasonable sample in at least one phase
    df['eligible'] = ((df['pp_balls'] >= pp_min) | (df['death_balls'] >= death_min))
    eligible = df[df['eligible']].copy()
    eligible = eligible.sort_values('composite_sos')
    topn = eligible.head(top)
    with open(out_md, 'w', encoding='utf-8') as f:
        f.write('# S3 CEO Shortlist (SOS-filtered, sample thresholds)\n\n')
        f.write('Date: May 25, 2026\n\n')
        for i, r in enumerate(topn.itertuples(), 1):
            f.write(f"{i}. {r.bowler}\n")
            f.write(f"   - PP econ (SOS): {r.pp_econ_sos} ({int(r.pp_balls)} balls), Death econ (SOS): {r.death_econ_sos} ({int(r.death_balls)} balls)\n")
            f.write(f"   - Composite (SOS): {r.composite_sos:.3f}\n\n")


if __name__ == '__main__':
    select()
