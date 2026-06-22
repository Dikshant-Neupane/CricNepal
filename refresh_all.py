#!/usr/bin/env python
"""
CricNepal Core Pipeline Orchestrator — refresh_all.py
Chains preprocessing, feature preparation, analytical models, and deliverables sync.
Ensures zero data drift and prevents stale-data bugs.
"""

import sys
import os
import subprocess
import time
from pathlib import Path

# Ensure standard output uses UTF-8 to prevent charmap encoder crashes on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

# Set working directory to project root
PROJECT_ROOT = Path(__file__).resolve().parent
os.chdir(PROJECT_ROOT)

# List of steps to run sequentially (scripts as relative paths to project root)
PIPELINE_STEPS = [
    # 1. Preprocessing & Normalization
    ("Data Normalization & Backfill", "src/preprocessing/normalize_data.py"),
    
    # 2. Team ELO Ratings
    ("Rolling Team ELO Ratings", "scripts/compute_team_elo.py"),
    
    # 3. Feature Prep
    ("Season Bowler Features", "scripts/prepare_season_features.py"),
    ("Extended Bowler Features", "scripts/prepare_features_extended.py"),
    
    # 4. Analytics & Diagnoses
    ("Root Cause Analysis", "src/analytics/root_cause_analysis.py"),
    ("Player Attribution Analysis", "src/analytics/player_attribution_analysis.py"),
    ("Opposition Strength Analysis", "src/analytics/opposition_strength_analysis.py"),
    ("S3 Performance Forecaster", "src/analytics/s3_performance_forecaster.py"),
    ("Win Probability Model", "src/analytics/win_probability_model.py"),
    ("Player Clustering", "src/analytics/player_clustering.py"),
    ("Attribution Sensitivity Analysis", "src/analytics/attribution_sensitivity_analysis.py"),
    ("Captaincy Hypothesis Analysis", "src/analytics/captaincy_analysis.py"),
    ("Death Batting Analysis", "src/analytics/death_batting_two_tier_analysis.py"),
    ("Death Bowling Analysis", "src/analytics/death_bowling_two_tier_analysis.py"),
    ("Dew Factor Analysis", "src/analytics/league_dew_factor_analysis.py"),
    ("Middle Overs Analysis", "src/analytics/middle_overs_analysis.py"),
    ("Powerplay Analysis", "src/analytics/powerplay_analysis.py"),
    ("Regression to Mean Analysis", "src/analytics/regression_to_mean_analysis.py"),
    ("Tactical Audit", "src/analytics/tactical_audit.py"),
    
    # 5. Sync Deliverables
    ("Deliverables & Exports Sync", "scripts/sync_deliverables.py")
]

def run_step(name: str, script_path: str) -> bool:
    """Run a single python script step and track success."""
    print(f"\n[Running] {name} ({script_path})...")
    start_time = time.time()
    
    # Use the active python interpreter to run the script
    python_exe = sys.executable
    
    try:
        # Run script with stdout/stderr preserved or captured depending on user preference
        # We run it inline so errors are clearly visible. Set environment variables to force UTF-8 output
        sub_env = os.environ.copy()
        sub_env["PYTHONIOENCODING"] = "utf-8"
        sub_env["PYTHONUTF8"] = "1"
        sub_env["PYTHONPATH"] = str(PROJECT_ROOT)
        res = subprocess.run([python_exe, script_path], check=True, capture_output=True, text=True, env=sub_env, encoding="utf-8")
        elapsed = time.time() - start_time
        print(f"[Completed] {name} in {elapsed:.2f}s")
        # If there's any stdout output, we show a brief preview
        if res.stdout:
            lines = res.stdout.strip().split("\n")
            preview = "\n".join(lines[-3:]) if len(lines) > 3 else res.stdout.strip()
            print(f"   Output preview:\n{preview}")
        return True
    except subprocess.CalledProcessError as e:
        elapsed = time.time() - start_time
        print(f"[Failed] {name} after {elapsed:.2f}s")
        print(f"   Command: {e.cmd}")
        print(f"   Exit code: {e.returncode}")
        if e.stdout:
            print(f"   --- Standard Output ---\n{e.stdout}")
        if e.stderr:
            print(f"   --- Error Output ---\n{e.stderr}")
        return False

def main():
    print("=" * 80)
    print("CRICNEPAL AUTOMATED PERFORMANCE PIPELINE REFRESH")
    print("=" * 80)
    print(f"Workspace Root: {PROJECT_ROOT}")
    print(f"Python Binary:  {sys.executable}")
    print(f"Total Steps:    {len(PIPELINE_STEPS)}")
    print("=" * 80)
    
    success_count = 0
    failures = []
    
    start_all = time.time()
    
    for name, script in PIPELINE_STEPS:
        full_script_path = PROJECT_ROOT / script
        if not full_script_path.exists():
            print(f"[Skipped] {name} - File not found: {script}")
            failures.append((name, "File not found"))
            continue
            
        success = run_step(name, script)
        if success:
            success_count += 1
        else:
            failures.append((name, "Runtime error"))
            # If preprocessing or elo fails, stop early as subsequent steps will fail or have stale data
            if script in ["src/preprocessing/normalize_data.py", "scripts/compute_team_elo.py", "scripts/prepare_season_features.py"]:
                print("\n[CRITICAL] PIPELINE FAILURES DETECTED. Stopping execution.")
                break
                
    elapsed_all = time.time() - start_all
    
    print("\n" + "=" * 80)
    print("PIPELINE SUMMARY")
    print("=" * 80)
    print(f"Duration:       {elapsed_all:.2f} seconds")
    print(f"Status:         {success_count} / {len(PIPELINE_STEPS)} completed successfully")
    
    if failures:
        print("\n[FAILED/SKIPPED] steps:")
        for name, reason in failures:
            print(f"  - {name}: {reason}")
        sys.exit(1)
    else:
        print("\n[SUCCESS] ALL PIPELINE STEPS IN SYNC!")
        print("Deliverables synced and ready for deployment.")
        sys.exit(0)

if __name__ == "__main__":
    main()
