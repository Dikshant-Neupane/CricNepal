import pandas as pd
import sys

fn = sys.argv[1] if len(sys.argv) > 1 else 'data/normalized/ball_by_ball_normalized.parquet'
df = pd.read_parquet(fn)
print('COLUMNS:', list(df.columns))
print('\nSAMPLE:')
print(df.head(5).to_dict())
