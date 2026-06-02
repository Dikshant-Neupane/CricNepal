"""
Tests for Decision Intelligence Service - Day 6
"""
import pytest
from src.dashboard.services.decision_intelligence import (
    generate_executive_recommendations,
    generate_phase_recommendations,
    format_recommendation_card
)


def test_generate_executive_recommendations_with_valid_data():
    """Test executive recommendations generation with valid S1/S2 data"""
    season_kpis = {
        "S1": {"win_pct": 50.0, "nrr": 0.250},
        "S2": {"win_pct": 25.0, "nrr": -0.350}
    }
    quality_score = 92
    
    recommendations = generate_executive_recommendations(season_kpis, quality_score)
    
    assert isinstance(recommendations, list)
    assert len(recommendations) > 0
    assert recommendations[0]["priority"] == 1
    assert "Win Rate Decline" in recommendations[0]["label"]
    assert "25.0" in recommendations[0]["text"]


def test_generate_executive_recommendations_handles_missing_data():
    """Test that missing season data returns appropriate message"""
    season_kpis = {}
    quality_score = 92
    
    recommendations = generate_executive_recommendations(season_kpis, quality_score)
    
    assert len(recommendations) == 1
    assert recommendations[0]["type"] == "warning"
    assert "Data Unavailable" in recommendations[0]["label"]


def test_generate_executive_recommendations_detects_nrr_decline():
    """Test NRR decline detection"""
    season_kpis = {
        "S1": {"win_pct": 50.0, "nrr": 0.500},
        "S2": {"win_pct": 48.0, "nrr": -0.100}
    }
    quality_score = 92
    
    recommendations = generate_executive_recommendations(season_kpis, quality_score)
    
    # Should have NRR decline recommendation
    nrr_recs = [r for r in recommendations if "Run Rate" in r["label"]]
    assert len(nrr_recs) > 0
    assert "-0.6" in nrr_recs[0]["text"] or "0.600" in nrr_recs[0]["text"]


def test_generate_executive_recommendations_detects_positive_trend():
    """Test positive trend detection"""
    season_kpis = {
        "S1": {"win_pct": 30.0, "nrr": -0.200},
        "S2": {"win_pct": 45.0, "nrr": 0.100}
    }
    quality_score = 95
    
    recommendations = generate_executive_recommendations(season_kpis, quality_score)
    
    # Should have positive momentum recommendation
    positive_recs = [r for r in recommendations if r["type"] == "success"]
    assert len(positive_recs) > 0
    assert "Positive Momentum" in positive_recs[0]["label"]


def test_generate_phase_recommendations_powerplay_decline():
    """Test powerplay-specific recommendations for decline"""
    s1_stats = {"run_rate": 8.5, "dot_pct": 30.0, "boundary_pct": 18.0}
    s2_stats = {"run_rate": 7.5, "dot_pct": 35.0, "boundary_pct": 15.0}
    
    recs = generate_phase_recommendations(s1_stats, s2_stats, "powerplay")
    
    assert "insight" in recs
    assert "risk" in recs
    assert "action" in recs
    assert "declined" in recs["insight"].lower()
    assert "1.00" in recs["insight"] or "1.0" in recs["insight"]


def test_generate_phase_recommendations_middle_overs():
    """Test middle overs recommendations"""
    s1_stats = {"run_rate": 9.0, "dot_pct": 28.0, "boundary_pct": 20.0}
    s2_stats = {"run_rate": 8.0, "dot_pct": 32.0, "boundary_pct": 18.0}
    
    recs = generate_phase_recommendations(s1_stats, s2_stats, "middle")
    
    assert "Middle overs" in recs["insight"]
    assert "action" in recs


def test_generate_phase_recommendations_death_overs():
    """Test death overs recommendations"""
    s1_stats = {"run_rate": 11.0, "dot_pct": 22.0, "boundary_pct": 28.0}
    s2_stats = {"run_rate": 9.5, "dot_pct": 26.0, "boundary_pct": 24.0}
    
    recs = generate_phase_recommendations(s1_stats, s2_stats, "death")
    
    assert "Death overs" in recs["insight"]
    assert "16-20" in recs["action"] or "17-20" in recs["action"]


def test_generate_phase_recommendations_stable_phase():
    """Test stable phase (no decline) recommendations"""
    s1_stats = {"run_rate": 8.0, "dot_pct": 30.0, "boundary_pct": 18.0}
    s2_stats = {"run_rate": 8.2, "dot_pct": 29.0, "boundary_pct": 19.0}
    
    recs = generate_phase_recommendations(s1_stats, s2_stats, "powerplay")
    
    assert "stable or improved" in recs["insight"].lower()


def test_format_recommendation_card_generates_html():
    """Test HTML card formatting"""
    recommendations = [
        {
            "priority": 1,
            "type": "error",
            "label": "Critical Issue",
            "text": "Test recommendation text."
        }
    ]
    
    html = format_recommendation_card(recommendations, title="Test Priorities")
    
    assert "<div class=\"card\">" in html
    assert "Test Priorities" in html
    assert "Critical Issue" in html
    assert "Test recommendation text." in html


def test_format_recommendation_card_handles_empty_list():
    """Test empty recommendations list"""
    html = format_recommendation_card([], title="No Recommendations")
    
    assert "<div class=\"card\">" in html
    assert "No recommendations available" in html


def test_format_recommendation_card_handles_multiple_types():
    """Test card with multiple recommendation types"""
    recommendations = [
        {"priority": 1, "type": "error", "label": "Critical", "text": "Fix this."},
        {"priority": 2, "type": "warning", "label": "Warning", "text": "Monitor this."},
        {"priority": 3, "type": "success", "label": "Good", "text": "Continue this."}
    ]
    
    html = format_recommendation_card(recommendations)
    
    assert "insight-box-error" in html
    assert "insight-box-warning" in html
    assert "insight-box-success" in html
    assert "#1 —" in html
    assert "#2 —" in html
    assert "#3 —" in html
