"""Data quality checks for dashboard-ready match records."""

from __future__ import annotations

import pandas as pd

REQUIRED_MATCH_FIELDS = [
    "season",
    "competition_name",
    "competition_tier",
    "opposition_strength_bucket",
    "match_context",
    "result",
    "runs_for",
    "runs_against",
    "overs_faced",
    "overs_bowled",
]

_ALLOWED_TIERS = {"A", "B", "C"}
_ALLOWED_CONTEXT = {"league", "knockout", "high-pressure"}
_ALLOWED_OPPOSITION_BUCKETS = {"strong", "balanced", "weak"}
_ALLOWED_RESULTS = {"W", "L", "NR"}


def _as_non_null_rate(series: pd.Series) -> float:
    if len(series) == 0:
        return 0.0
    return float(series.notna().sum() / len(series))


def validate_match_records(df: pd.DataFrame) -> dict:
    """Validate schema and key tactical fields for dashboard reliability."""
    findings: list[dict] = []

    missing_columns = [col for col in REQUIRED_MATCH_FIELDS if col not in df.columns]
    if missing_columns:
        findings.append(
            {
                "level": "error",
                "message": "Missing required columns",
                "details": ", ".join(missing_columns),
            }
        )

    if not missing_columns:
        non_null_rates = {col: _as_non_null_rate(df[col]) for col in REQUIRED_MATCH_FIELDS}
        low_completeness = [
            f"{col}: {rate * 100:.1f}%"
            for col, rate in non_null_rates.items()
            if rate < 0.95
        ]
        if low_completeness:
            findings.append(
                {
                    "level": "warning",
                    "message": "Required fields below 95% completeness",
                    "details": "; ".join(low_completeness),
                }
            )

        invalid_tiers = sorted(set(df.loc[~df["competition_tier"].isin(_ALLOWED_TIERS), "competition_tier"].dropna()))
        if invalid_tiers:
            findings.append(
                {
                    "level": "error",
                    "message": "Invalid competition_tier values",
                    "details": ", ".join(map(str, invalid_tiers)),
                }
            )

        invalid_context = sorted(set(df.loc[~df["match_context"].isin(_ALLOWED_CONTEXT), "match_context"].dropna()))
        if invalid_context:
            findings.append(
                {
                    "level": "error",
                    "message": "Invalid match_context values",
                    "details": ", ".join(map(str, invalid_context)),
                }
            )

        invalid_opposition = sorted(
            set(df.loc[~df["opposition_strength_bucket"].isin(_ALLOWED_OPPOSITION_BUCKETS), "opposition_strength_bucket"].dropna())
        )
        if invalid_opposition:
            findings.append(
                {
                    "level": "error",
                    "message": "Invalid opposition_strength_bucket values",
                    "details": ", ".join(map(str, invalid_opposition)),
                }
            )

        invalid_results = sorted(set(df.loc[~df["result"].isin(_ALLOWED_RESULTS), "result"].dropna()))
        if invalid_results:
            findings.append(
                {
                    "level": "error",
                    "message": "Invalid result values",
                    "details": ", ".join(map(str, invalid_results)),
                }
            )

        # Data consistency checks
        zero_runs_records = len(df[(df["runs_for"] == 0) & (df["runs_against"] == 0)])
        if zero_runs_records > 0:
            findings.append(
                {
                    "level": "warning",
                    "message": f"{zero_runs_records} records with zero runs (may indicate missing ball-by-ball data)",
                    "details": "Check if runs data is populated correctly",
                }
            )
        
        # Overs validation (should be between 0 and 20 for T20)
        invalid_overs = len(df[(df["overs_faced"] > 20.0) | (df["overs_bowled"] > 20.0)])
        if invalid_overs > 0:
            findings.append(
                {
                    "level": "error",
                    "message": f"{invalid_overs} records with overs > 20 (invalid for T20)",
                    "details": "Overs should not exceed 20 in T20 format",
                }
            )
        
        # Season distribution check
        season_counts = df["season"].value_counts().to_dict()
        if "S1" in season_counts and "S2" in season_counts:
            findings.append(
                {
                    "level": "info",
                    "message": f"Multi-season data available: S1={season_counts.get('S1', 0)}, S2={season_counts.get('S2', 0)}",
                    "details": "Good coverage for season comparison analysis",
                }
            )

    total_rows = int(len(df))
    error_count = sum(1 for item in findings if item["level"] == "error")
    warning_count = sum(1 for item in findings if item["level"] == "warning")
    info_count = sum(1 for item in findings if item["level"] == "info")
    
    # Calculate reliability score
    score = 100 - (error_count * 20) - (warning_count * 8)
    reliability_score = max(0, score)

    status = "healthy" if error_count == 0 else "degraded" if warning_count > 0 else "blocked"

    return {
        "status": status,
        "total_rows": total_rows,
        "error_count": error_count,
        "warning_count": warning_count,
        "info_count": info_count,
        "reliability_score": reliability_score,
        "findings": findings,
    }
