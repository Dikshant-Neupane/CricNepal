"""
Tests for UI patterns component - Day 5: Test and QA Layer
"""
import streamlit as st
from unittest.mock import MagicMock, patch, call
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


def test_ui_patterns_imports():
    """Test that all UI pattern functions can be imported"""
    from dashboard.components.ui_patterns import (
        render_card_header,
        render_card_start,
        render_card_end,
        render_spacer,
        render_insight_box,
        render_insight_card,
        render_section_header,
        render_page_header,
        render_table_card,
    )
    
    # Check all functions are callable
    assert callable(render_card_header)
    assert callable(render_card_start)
    assert callable(render_card_end)
    assert callable(render_spacer)
    assert callable(render_insight_box)
    assert callable(render_insight_card)
    assert callable(render_section_header)
    assert callable(render_page_header)
    assert callable(render_table_card)


@patch('dashboard.components.ui_patterns.st.markdown')
def test_render_spacer_generates_correct_html(mock_markdown):
    """Test spacer renders with correct height"""
    from dashboard.components.ui_patterns import render_spacer
    
    render_spacer(32)
    
    mock_markdown.assert_called_once()
    call_args = mock_markdown.call_args[0][0]
    assert "height: 32px" in call_args
    assert "<div" in call_args


@patch('dashboard.components.ui_patterns.st.markdown')
def test_render_page_header_includes_all_components(mock_markdown):
    """Test page header includes title, subtitle, and insight alert"""
    from dashboard.components.ui_patterns import render_page_header
    
    render_page_header(
        title="Test Title",
        subtitle="Test Subtitle",
        insight_label="Test Label",
        insight_text="Test Text",
        alert_icon="⚠️"
    )
    
    mock_markdown.assert_called_once()
    call_args = mock_markdown.call_args[0][0]
    assert "Test Title" in call_args
    assert "Test Subtitle" in call_args
    assert "Test Label" in call_args
    assert "Test Text" in call_args
    assert "⚠️" in call_args
    assert "jb-page-head" in call_args


@patch('dashboard.components.ui_patterns.st.markdown')
def test_render_card_start_and_end_create_proper_structure(mock_markdown):
    """Test card start/end create opening and closing divs"""
    from dashboard.components.ui_patterns import render_card_start, render_card_end
    
    render_card_start("Test Card", "Test Subtitle")
    render_card_end()
    
    assert mock_markdown.call_count == 2
    
    # First call should have opening tags
    first_call = mock_markdown.call_args_list[0][0][0]
    assert "<div class=\"card\">" in first_call
    assert "Test Card" in first_call
    assert "Test Subtitle" in first_call
    
    # Second call should have closing tags
    second_call = mock_markdown.call_args_list[1][0][0]
    assert "</div></div>" in second_call


@patch('dashboard.components.ui_patterns.st.markdown')
def test_render_insight_card_handles_multiple_insights(mock_markdown):
    """Test insight card renders multiple insight boxes"""
    from dashboard.components.ui_patterns import render_insight_card
    
    insights = [
        {"label": "Insight", "text": "Test insight 1", "type": "neutral"},
        {"label": "Risk", "text": "Test risk", "type": "warning"},
        {"label": "Action", "text": "Test action", "type": "neutral"},
    ]
    
    render_insight_card("Test Card", insights)
    
    mock_markdown.assert_called_once()
    call_args = mock_markdown.call_args[0][0]
    
    # Check all insights are present
    assert "Test insight 1" in call_args
    assert "Test risk" in call_args
    assert "Test action" in call_args
    assert "Insight:" in call_args
    assert "Risk:" in call_args
    assert "Action:" in call_args


@patch('dashboard.components.ui_patterns.st.markdown')
def test_render_table_card_creates_table_structure(mock_markdown):
    """Test table card creates proper table HTML"""
    from dashboard.components.ui_patterns import render_table_card
    
    headers = ["Col1", "Col2", "Col3"]
    rows = [
        ["A", "B", "C"],
        ["D", "E", "F"],
    ]
    column_classes = ["", "right", "right"]
    
    render_table_card("Test Table", headers, rows, column_classes)
    
    mock_markdown.assert_called_once()
    call_args = mock_markdown.call_args[0][0]
    
    # Check table structure
    assert "<table" in call_args
    assert "<thead>" in call_args
    assert "<tbody>" in call_args
    assert "Col1" in call_args
    assert "Col2" in call_args
    assert "Col3" in call_args
    assert "A" in call_args and "B" in call_args and "C" in call_args
    assert "D" in call_args and "E" in call_args and "F" in call_args
    assert 'class="right"' in call_args


def test_render_insight_box_types():
    """Test insight box handles different box types"""
    from dashboard.components.ui_patterns import render_insight_box
    
    with patch('dashboard.components.ui_patterns.st.markdown') as mock_markdown:
        render_insight_box("Test", "Text", "neutral")
        neutral_call = mock_markdown.call_args[0][0]
        assert "insight-box" in neutral_call
    
    with patch('dashboard.components.ui_patterns.st.markdown') as mock_markdown:
        render_insight_box("Test", "Text", "warning")
        warning_call = mock_markdown.call_args[0][0]
        assert "insight-box-warning" in warning_call
    
    with patch('dashboard.components.ui_patterns.st.markdown') as mock_markdown:
        render_insight_box("Test", "Text", "success")
        success_call = mock_markdown.call_args[0][0]
        assert "insight-box-success" in success_call
