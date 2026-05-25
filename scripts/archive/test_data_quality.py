import sys
sys.path.insert(0, "d:/CricNepal")

from src.dashboard.services.data_source import load_match_records
from src.dashboard.services.data_quality import validate_match_records

# Load real data
df, source = load_match_records()

print(f"Data Source: {source}")
print(f"Number of matches: {len(df)}")

# Validate
quality_report = validate_match_records(df)

print(f"\n{'='*60}")
print(f"DATA QUALITY REPORT")
print(f"{'='*60}")
print(f"Status: {quality_report['status']}")
print(f"Reliability Score: {quality_report['reliability_score']}")
print(f"Errors: {quality_report['error_count']}")
print(f"Warnings: {quality_report['warning_count']}")
print(f"Total Rows: {quality_report['total_rows']}")

if quality_report['findings']:
    print(f"\n{'='*60}")
    print(f"FINDINGS:")
    print(f"{'='*60}")
    for finding in quality_report['findings']:
        print(f"\n{finding['level'].upper()}: {finding['message']}")
        print(f"Details: {finding['details']}")

# Check the actual data values
print(f"\n{'='*60}")
print(f"DATA INSPECTION:")
print(f"{'='*60}")
print(f"\nCompetition Tiers: {df['competition_tier'].unique()}")
print(f"Match Contexts: {df['match_context'].unique()}")
print(f"Opposition Buckets: {df['opposition_strength_bucket'].unique()}")
print(f"Results: {df['result'].unique()}")
