"""
Smoke tests for Janakpur Bolts Dashboard
Day 1: Stabilization Baseline - Import and Module Checks
"""
import sys
from pathlib import Path

# Add src to path - this mimics how the Streamlit app imports modules
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Also ensure parent directory is in path
parent_path = Path(__file__).parent.parent
sys.path.insert(0, str(parent_path))

def test_imports():
    """Test all dashboard page modules can be imported"""
    print("=" * 60)
    print("DASHBOARD MODULE IMPORT SMOKE TEST")
    print("=" * 60)
    
    modules = [
        "dashboard.page_modules.executive_overview",
        "dashboard.page_modules.team_decline_analysis",
        "dashboard.page_modules.batting_intelligence",
        "dashboard.page_modules.bowling_intelligence",
        "dashboard.page_modules.phase_analysis",
        "dashboard.page_modules.player_archetypes",
        "dashboard.page_modules.matchups",
        "dashboard.page_modules.match_review",
        "dashboard.page_modules.opposition_report",
        "dashboard.page_modules.win_probability",
        "dashboard.page_modules.s3_recruiting",
        "dashboard.page_modules.s3_strategic_analysis",
    ]
    
    results = {"passed": [], "failed": []}
    
    for module_name in modules:
        try:
            __import__(module_name)
            results["passed"].append(module_name)
            print(f"✅ {module_name}")
        except Exception as e:
            results["failed"].append((module_name, str(e)))
            print(f"❌ {module_name}: {e}")
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {len(results['passed'])} passed, {len(results['failed'])} failed")
    print("=" * 60)
    
    if results["failed"]:
        print("\n❌ FAILED MODULES:")
        for mod, err in results["failed"]:
            print(f"  - {mod}")
            print(f"    Error: {err[:100]}")
        return False
    
    print("\n✅ All modules imported successfully!")
    return True


def test_data_loaders():
    """Test data loader service"""
    print("\n" + "=" * 60)
    print("DATA LOADER SERVICE TEST")
    print("=" * 60)
    
    try:
        from dashboard.services.data_source import load_match_records
        from dashboard.services.data_loaders import (
            load_export_csv,
            export_path,
            load_ball_by_ball_normalized,
            load_team_matches_for
        )
        from dashboard.services.data_quality import validate_match_records
        
        print("✅ Data source functions imported")
        print("✅ Data loader functions imported")
        print("✅ Data quality validator imported")
        
        # Test export path helper
        test_path = export_path("test.csv")
        print(f"✅ Export path helper: {test_path}")
        
        # Test data quality validation
        df, source = load_match_records()
        report = validate_match_records(df)
        print(f"✅ Data quality: {report['status']} (score: {report['reliability_score']}/100)")
        print(f"   └─ {report['total_rows']} records, {report['error_count']} errors, {report['warning_count']} warnings")
        
        return True
    except Exception as e:
        print(f"❌ Data loader test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_theme():
    """Test theme module"""
    print("\n" + "=" * 60)
    print("THEME MODULE TEST")
    print("=" * 60)
    
    try:
        from dashboard import theme
        print("✅ Theme module imported")
        
        # Check if inject_css function exists
        if hasattr(theme, 'inject_css'):
            print("✅ inject_css function found")
        else:
            print("⚠️  inject_css function not found")
        
        return True
    except Exception as e:
        print(f"❌ Theme test failed: {e}")
        return False


def test_ui_components():
    """Test UI components and patterns (Day 4)"""
    print("\n" + "=" * 60)
    print("UI COMPONENTS TEST")
    print("=" * 60)
    
    try:
        from dashboard.components.ui_patterns import (
            render_page_header,
            render_card_start,
            render_card_end,
            render_spacer,
            render_insight_card,
            render_table_card
        )
        from dashboard.components.match_summary import (
            render_match_summary,
            render_tactical_takeaways,
            render_phase_table,
            render_partnerships_table
        )
        from dashboard.components.metric_card import (
            render_metric_card,
            render_metric_row
        )
        
        print("✅ UI patterns component imported")
        print("✅ Match summary components imported")
        print("✅ Metric card components imported")
        
        return True
    except Exception as e:
        print(f"❌ UI components test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_metrics_service():
    """Test enhanced metrics service (Day 3)"""
    print("\n" + "=" * 60)
    print("METRICS SERVICE TEST")
    print("=" * 60)
    
    try:
        from dashboard.services.metrics import (
            compute_team_kpis,
            compute_season_kpis,
            compute_season_delta,
            compute_form_index,
            compute_weighted_form_index,
            build_executive_cards
        )
        
        print("✅ compute_team_kpis imported")
        print("✅ compute_season_kpis imported (Day 3)")
        print("✅ compute_season_delta imported (Day 3)")
        print("✅ compute_form_index imported (Day 3)")
        print("✅ compute_weighted_form_index imported")
        print("✅ build_executive_cards imported")
        
        # Quick functional test
        import pandas as pd
        sample_df = pd.DataFrame([
            {
                "season": "S1",
                "competition_name": "NPL Season 1",
                "result": "W",
                "runs_for": 180,
                "runs_against": 170,
                "overs_faced": 20.0,
                "overs_bowled": 20.0,
            }
        ])
        
        kpis = compute_team_kpis(sample_df)
        print(f"✅ compute_team_kpis functional: win_pct={kpis['win_pct']}")
        
        season_kpis = compute_season_kpis(sample_df)
        print(f"✅ compute_season_kpis functional: {len(season_kpis)} season(s)")
        
        form = compute_form_index(sample_df)
        print(f"✅ compute_form_index functional: form={form}")
        
        return True
    except Exception as e:
        print(f"❌ Metrics service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n🔍 Starting Dashboard Smoke Tests...\n")
    
    all_passed = True
    all_passed &= test_imports()
    all_passed &= test_data_loaders()
    all_passed &= test_theme()
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL SMOKE TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 60)
    
    sys.exit(0 if all_passed else 1)
