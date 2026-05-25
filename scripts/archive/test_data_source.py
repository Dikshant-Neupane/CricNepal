import sys
sys.path.insert(0, "d:/CricNepal")

from src.dashboard.services.data_source import load_match_records

# Test the parquet loading
df, source = load_match_records()

print(f"Data Source: {source}")
print(f"Number of matches: {len(df)}")
print(f"\nColumns: {df.columns.tolist()}")
print(f"\nFirst few matches:")
print(df.head())
print(f"\nSeasons: {df['season'].value_counts()}")
print(f"\nResults: {df['result'].value_counts()}")
