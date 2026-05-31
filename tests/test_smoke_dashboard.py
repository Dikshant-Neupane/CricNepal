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
        print("✅ Data source functions imported")
        print("✅ Data loader functions imported")
        
        # Test export path helper
        test_path = export_path("test.csv")
        print(f"✅ Export path helper: {test_path}")
        
        return True
    except Exception as e:
        print(f"❌ Data loader test failed: {e}")
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
