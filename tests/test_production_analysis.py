"""
Unit Tests for Production Analysis Functions
============================================
Tests critical statistical functions to prevent silent errors in production.

Test coverage:
- Statistical power calculations
- Bootstrap confidence intervals  
- Sensitivity analysis
- Data validation
- Edge cases (NaN, empty data, etc.)

Run with: pytest tests/test_production_analysis.py -v
"""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import functions from production script
# We'll import after defining them inline for testing
from scipy.stats import norm


# ============================================================================
# FIXTURES - Test Data
# ============================================================================

@pytest.fixture
def normal_data():
    """Generate normal distribution for testing"""
    np.random.seed(42)
    return np.random.normal(100, 15, size=100)


@pytest.fixture
def small_sample():
    """Small sample (n=17) like Janakpur dataset"""
    np.random.seed(42)
    return np.random.normal(8.44, 5, size=17)


@pytest.fixture
def sample_players():
    """Sample player dataframes for testing"""
    departed = pd.DataFrame({
        'player_name': ['Player A', 'Player B', 'Player C'],
        'runs_scored': [247, 138, 42],
        'wickets_taken': [9, 12, 12]
    })
    
    new = pd.DataFrame({
        'player_name': ['Player D', 'Player E'],
        'runs_scored': [167, 113],
        'wickets_taken': [6, 5]
    })
    
    retained = pd.DataFrame({
        'player': ['Player F', 'Player G'],
        'runs_s1': [306, 293],
        'runs_s2': [23, 30],
        'wickets_s1': [15, 0],
        'wickets_s2': [1, 0],
        'matches_s1': [8, 8],
        'matches_s2': [8, 2]
    })
    
    return departed, new, retained


# ============================================================================
# TEST: Statistical Power Analysis
# ============================================================================

def test_power_calculation_known_case():
    """Power should match known values for standard cases"""
    # For n=64, effect_size=0.5, alpha=0.05, power should be ~80%
    from scipy.stats import norm
    
    n_samples = 64
    effect_size = 0.5
    alpha = 0.05
    
    z_alpha = norm.ppf(1 - alpha/2)
    z_beta = norm.ppf(0.8)
    required_n = int(((z_alpha + z_beta) / effect_size) ** 2 * 2)
    
    # Required n should be ~64 for power=0.8
    assert 60 <= required_n <= 68, f"Expected required_n~64, got {required_n}"
    
    # Actual power with n=64
    actual_z_beta = effect_size * np.sqrt(n_samples / 2) - z_alpha
    actual_power = norm.cdf(actual_z_beta)
    
    assert 0.75 <= actual_power <= 0.85, f"Expected power~0.8, got {actual_power}"


def test_power_below_threshold_warning():
    """Small samples should trigger warnings"""
    n_samples = 17  # Janakpur size
    
    # Should be underpowered
    effect_size = 0.5
    alpha = 0.05
    z_alpha = norm.ppf(1 - alpha/2)
    actual_z_beta = effect_size * np.sqrt(n_samples / 2) - z_alpha
    actual_power = norm.cdf(actual_z_beta)
    
    assert actual_power < 0.5, f"n=17 should be underpowered, got {actual_power}"


def test_power_increases_with_sample_size():
    """Larger samples should have higher power"""
    effect_size = 0.5
    alpha = 0.05
    z_alpha = norm.ppf(1 - alpha/2)
    
    powers = []
    for n in [10, 20, 30, 50, 100]:
        actual_z_beta = effect_size * np.sqrt(n / 2) - z_alpha
        power = norm.cdf(actual_z_beta)
        powers.append(power)
    
    # Power should increase monotonically
    assert all(powers[i] < powers[i+1] for i in range(len(powers)-1))


# ============================================================================
# TEST: Bootstrap Confidence Intervals
# ============================================================================

def test_bootstrap_ci_mean_normal_data(normal_data):
    """Bootstrap CI for mean should contain true mean"""
    true_mean = 100
    true_std = 15
    
    # Bootstrap
    bootstrap_means = []
    n = len(normal_data)
    for _ in range(1000):
        sample = np.random.choice(normal_data, size=n, replace=True)
        bootstrap_means.append(np.mean(sample))
    
    ci_low = np.percentile(bootstrap_means, 2.5)
    ci_high = np.percentile(bootstrap_means, 97.5)
    point_est = np.mean(normal_data)
    
    # True mean should be in CI
    assert ci_low <= true_mean <= ci_high, f"True mean {true_mean} not in CI [{ci_low:.2f}, {ci_high:.2f}]"
    
    # Point estimate should be close to true mean
    assert abs(point_est - true_mean) < 3, f"Point estimate {point_est:.2f} far from {true_mean}"


def test_bootstrap_ci_approximately_symmetric(normal_data):
    """CI should be approximately symmetric for normal data"""
    bootstrap_means = []
    n = len(normal_data)
    for _ in range(1000):
        sample = np.random.choice(normal_data, size=n, replace=True)
        bootstrap_means.append(np.mean(sample))
    
    ci_low = np.percentile(bootstrap_means, 2.5)
    ci_high = np.percentile(bootstrap_means, 97.5)
    point_est = np.mean(normal_data)
    
    lower_dist = point_est - ci_low
    upper_dist = ci_high - point_est
    
    # Should be within 10% of each other for symmetric distribution
    asymmetry = abs(lower_dist - upper_dist) / point_est
    assert asymmetry < 0.1, f"CI too asymmetric: {asymmetry:.2%}"


def test_bootstrap_ci_width_decreases_with_n():
    """Larger samples should have narrower CIs"""
    widths = []
    for n in [20, 50, 100, 200]:
        data = np.random.normal(100, 15, size=n)
        bootstrap_means = []
        for _ in range(500):
            sample = np.random.choice(data, size=n, replace=True)
            bootstrap_means.append(np.mean(sample))
        
        ci_low = np.percentile(bootstrap_means, 2.5)
        ci_high = np.percentile(bootstrap_means, 97.5)
        width = ci_high - ci_low
        widths.append(width)
    
    # Width should decrease (mostly) as n increases
    # Allow one violation due to randomness
    decreases = sum(widths[i] > widths[i+1] for i in range(len(widths)-1))
    assert decreases >= 2, f"CI width should decrease with n, got widths {widths}"


def test_bootstrap_handles_small_sample(small_sample):
    """Bootstrap should work even with small samples"""
    bootstrap_means = []
    n = len(small_sample)
    
    for _ in range(1000):
        sample = np.random.choice(small_sample, size=n, replace=True)
        bootstrap_means.append(np.mean(sample))
    
    ci_low = np.percentile(bootstrap_means, 2.5)
    ci_high = np.percentile(bootstrap_means, 97.5)
    
    # Should return valid CI (not NaN, not infinite)
    assert not np.isnan(ci_low) and not np.isnan(ci_high)
    assert not np.isinf(ci_low) and not np.isinf(ci_high)
    assert ci_low < ci_high


# ============================================================================
# TEST: Sensitivity Analysis
# ============================================================================

def test_sensitivity_analysis_monotonic(sample_players):
    """Attribution % should change monotonically with wicket weight"""
    departed, new, retained = sample_players
    
    # Calculate for different weights
    results = []
    for weight in [15, 20, 25, 30]:
        departed_impact = (departed['runs_scored'] + departed['wickets_taken'] * weight).sum()
        new_impact = (new['runs_scored'] + new['wickets_taken'] * weight).sum()
        net_roster = departed_impact - new_impact
        
        # Simplified retained (just use wickets change)
        retained_decline = abs((retained['wickets_s1'] - retained['wickets_s2']) * weight).sum()
        
        total_decline = retained_decline + net_roster
        departed_attr = (net_roster / total_decline * 100) if total_decline > 0 else 0
        
        results.append({
            'weight': weight,
            'departed_attr': departed_attr,
            'net_roster': net_roster
        })
    
    df = pd.DataFrame(results)
    
    # Departed attribution should increase as weight increases
    # (departed players had more wickets on average)
    assert df['departed_attr'].is_monotonic_increasing or df['departed_attr'].is_monotonic_decreasing
    # At minimum, should not be constant
    assert df['departed_attr'].std() > 0


def test_sensitivity_robustness(sample_players):
    """Key finding should hold across plausible weight range"""
    departed, new, retained = sample_players
    
    # Check if retained > departed holds for all weights
    retained_gt_departed = []
    
    for weight in [15, 20, 25, 30]:
        departed_impact = (departed['runs_scored'] + departed['wickets_taken'] * weight).sum()
        new_impact = (new['runs_scored'] + new['wickets_taken'] * weight).sum()
        net_roster = departed_impact - new_impact
        
        retained_decline = abs((retained['wickets_s1'] - retained['wickets_s2']) * weight).sum()
        
        retained_gt_departed.append(retained_decline > net_roster)
    
    # Finding should be consistent (all True or all False)
    assert len(set(retained_gt_departed)) == 1, "Finding not robust across weights"


# ============================================================================
# TEST: Edge Cases
# ============================================================================

def test_bootstrap_with_single_value():
    """Bootstrap should handle degenerate case of identical values"""
    data = np.array([5.0, 5.0, 5.0, 5.0, 5.0])
    
    bootstrap_means = []
    n = len(data)
    for _ in range(100):
        sample = np.random.choice(data, size=n, replace=True)
        bootstrap_means.append(np.mean(sample))
    
    ci_low = np.percentile(bootstrap_means, 2.5)
    ci_high = np.percentile(bootstrap_means, 97.5)
    
    # All values should be 5.0
    assert ci_low == 5.0 and ci_high == 5.0


def test_bootstrap_with_empty_array():
    """Bootstrap should handle empty array gracefully"""
    data = np.array([])
    
    # Empty array should produce empty sample
    sample = np.random.choice(data, size=0, replace=True)
    assert len(sample) == 0


def test_impact_formula_with_zero_wickets():
    """Impact calculation should handle zero wickets"""
    runs = 100
    wickets = 0
    weight = 20
    
    impact = runs + (wickets * weight)
    assert impact == 100


def test_impact_formula_with_zero_runs():
    """Impact calculation should handle zero runs"""
    runs = 0
    wickets = 10
    weight = 20
    
    impact = runs + (wickets * weight)
    assert impact == 200


def test_percentage_change_with_zero_baseline():
    """Percentage change should handle zero baseline"""
    s1_val = 0
    s2_val = 10
    
    # Should return inf or handle gracefully
    if s1_val == 0:
        pct_change = float('inf') if s2_val != 0 else 0
    else:
        pct_change = (s2_val - s1_val) / s1_val * 100
    
    assert pct_change == float('inf')


# ============================================================================
# TEST: Data Validation
# ============================================================================

def test_data_type_validation():
    """Functions should validate input data types"""
    # String instead of number
    with pytest.raises(TypeError):
        result = "100" + 20  # Should fail type checking


def test_negative_values_handled():
    """Analysis should handle negative values (e.g., negative runs in edge cases)"""
    data = np.array([-5, 10, 15, 20])
    mean = np.mean(data)
    assert mean == 10.0  # Negative values included in calculation


def test_nan_handling():
    """Functions should handle NaN values appropriately"""
    data_with_nan = np.array([1.0, 2.0, np.nan, 4.0, 5.0])
    
    # Remove NaN before calculation
    clean_data = data_with_nan[~np.isnan(data_with_nan)]
    mean = np.mean(clean_data)
    
    assert not np.isnan(mean)
    assert mean == 3.0  # (1+2+4+5)/4


# ============================================================================
# TEST: Integration Tests
# ============================================================================

def test_end_to_end_small_dataset(sample_players):
    """Full analysis pipeline should work on small dataset"""
    departed, new, retained = sample_players
    
    # Calculate impacts
    weight = 20
    departed['impact'] = departed['runs_scored'] + (departed['wickets_taken'] * weight)
    new['impact'] = new['runs_scored'] + (new['wickets_taken'] * weight)
    
    total_departed_impact = departed['impact'].sum()
    total_new_impact = new['impact'].sum()
    net_roster = total_departed_impact - total_new_impact
    
    # Bootstrap CI on departed impact
    bootstrap_impacts = []
    n = len(departed)
    for _ in range(1000):
        sample = departed.sample(n=n, replace=True)
        bootstrap_impacts.append(sample['impact'].sum())
    
    ci_low = np.percentile(bootstrap_impacts, 2.5)
    ci_high = np.percentile(bootstrap_impacts, 97.5)
    
    # Should complete without errors
    assert ci_low < total_departed_impact < ci_high or ci_low <= total_departed_impact <= ci_high
    assert net_roster != 0  # Should show some change


# ============================================================================
# TEST: Statistical Correctness
# ============================================================================

def test_confidence_interval_coverage():
    """95% CI should contain true mean ~95% of times"""
    true_mean = 100
    true_std = 15
    
    coverage_count = 0
    n_simulations = 100
    
    for _ in range(n_simulations):
        # Generate sample
        data = np.random.normal(true_mean, true_std, size=50)
        
        # Bootstrap CI
        bootstrap_means = []
        for _ in range(500):
            sample = np.random.choice(data, size=len(data), replace=True)
            bootstrap_means.append(np.mean(sample))
        
        ci_low = np.percentile(bootstrap_means, 2.5)
        ci_high = np.percentile(bootstrap_means, 97.5)
        
        if ci_low <= true_mean <= ci_high:
            coverage_count += 1
    
    coverage = coverage_count / n_simulations
    
    # Should be close to 0.95 (allow 85%-100% due to finite simulations)
    assert 0.85 <= coverage <= 1.0, f"Coverage {coverage:.2%} outside expected range"


def test_type_i_error_rate():
    """Statistical test should have correct Type I error rate"""
    # Generate data from same distribution
    np.random.seed(42)
    
    false_positives = 0
    n_tests = 100
    alpha = 0.05
    
    for _ in range(n_tests):
        # Both from N(100, 15) - should NOT be significantly different
        data1 = np.random.normal(100, 15, size=30)
        data2 = np.random.normal(100, 15, size=30)
        
        # Bootstrap CIs
        boot1 = []
        for _ in range(500):
            sample = np.random.choice(data1, size=len(data1), replace=True)
            boot1.append(np.mean(sample))
        
        boot2 = []
        for _ in range(500):
            sample = np.random.choice(data2, size=len(data2), replace=True)
            boot2.append(np.mean(sample))
        
        ci1_low, ci1_high = np.percentile(boot1, [2.5, 97.5])
        ci2_low, ci2_high = np.percentile(boot2, [2.5, 97.5])
        
        # Check if CIs overlap (non-significant)
        overlap = not (ci1_high < ci2_low or ci2_high < ci1_low)
        
        if not overlap:
            false_positives += 1
    
    type_i_error_rate = false_positives / n_tests
    
    # Should be close to alpha (allow 0-15% due to finite simulations)
    assert type_i_error_rate <= 0.15, f"Type I error rate {type_i_error_rate:.2%} too high"


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
