"""
Professional Material 3 Theme for Janakpur Bolts Dashboard
Matches the HTML mockup design system exactly.
"""

# Color constants for Python code
COLORS = {
    "primary": "#012d1d",
    "primary_container": "#1b4332",
    "secondary": "#2c694e",
    "secondary_container": "#aeeecb",
    "error": "#ba1a1a",
    "surface": "#f8f9fa",
    "outline": "#717973",
    "outline_variant": "#c1c8c2",
}


def get_theme_css() -> str:
    """
    Returns CSS that matches the professional HTML mockup design.
    Clean, modern Material 3 styling with proper card layouts.
    """
    return """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* ═══════════════════════════════════════════════════════════════
       MATERIAL 3 DESIGN TOKENS
       ═══════════════════════════════════════════════════════════════ */
    :root {
        /* Surface Colors */
        --surface: #f8f9fa;
        --surface-container-lowest: #ffffff;
        --surface-container-low: #f3f4f5;
        --surface-container: #edeeef;
        --surface-variant: #e1e3e4;
        
        /* Primary Colors */
        --primary: #012d1d;
        --primary-container: #1b4332;
        --on-primary: #ffffff;
        --on-primary-container: #86af99;
        
        /* Secondary Colors */
        --secondary: #2c694e;
        --secondary-container: #aeeecb;
        --on-secondary: #ffffff;
        
        /* Error Colors */
        --error: #ba1a1a;
        --error-container: #ffdad6;
        
        /* Text Colors */
        --on-surface: #191c1d;
        --on-surface-variant: #414844;
        
        /* Outline Colors */
        --outline: #717973;
        --outline-variant: #c1c8c2;
        
        /* Spacing */
        --sp-xs: 4px;
        --sp-sm: 12px;
        --sp-md: 24px;
        --sp-lg: 48px;
        --sp-gutter: 16px;
        
        /* Border Radius */
        --radius: 8px;
        
        /* Shadows */
        --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.05);
    }
    
    /* ═══════════════════════════════════════════════════════════════
       GLOBAL STYLES
       ═══════════════════════════════════════════════════════════════ */
    * {
        font-family: 'Inter', -apple-system, sans-serif !important;
    }
    
    html, body, [data-testid="stAppViewContainer"] {
        background-color: var(--surface) !important;
        color: var(--on-surface) !important;
    }
    
    /* Hide Streamlit branding */
    #MainMenu, footer, header {
        visibility: hidden;
    }
    
    /* ═══════════════════════════════════════════════════════════════
       PAGE HEADER
       ═══════════════════════════════════════════════════════════════ */
    .page-header {
        margin-bottom: var(--sp-md);
    }
    
    .page-title {
        font-size: 32px;
        font-weight: 600;
        line-height: 40px;
        letter-spacing: -0.01em;
        color: var(--on-surface);
        margin-bottom: var(--sp-xs);
    }
    
    .page-subtitle {
        font-size: 16px;
        font-weight: 400;
        line-height: 24px;
        color: var(--on-surface-variant);
        margin-top: var(--sp-sm);
    }
    
    /* ═══════════════════════════════════════════════════════════════
       INSIGHT ALERT BOX
       ═══════════════════════════════════════════════════════════════ */
    .insight-alert {
        background-color: rgba(255, 218, 214, 0.2);
        border: 1px solid rgba(186, 26, 26, 0.2);
        border-radius: var(--radius);
        padding: var(--sp-sm);
        margin-top: var(--sp-sm);
        display: flex;
        align-items: flex-start;
        gap: var(--sp-sm);
    }
    
    .insight-alert-icon {
        color: var(--error);
        font-size: 20px;
    }
    
    .insight-alert-text {
        font-size: 14px;
        line-height: 20px;
        color: var(--on-surface);
    }
    
    .insight-label {
        font-weight: 600;
        font-size: 14px;
    }
    
    /* ═══════════════════════════════════════════════════════════════
       METRIC CARD (KPI Cards)
       ═══════════════════════════════════════════════════════════════ */
    .metric-card {
        background-color: var(--surface-container-lowest);
        border: 1px solid rgba(193, 200, 194, 0.3);
        border-radius: var(--radius);
        padding: var(--sp-md);
        transition: box-shadow 0.2s ease;
    }
    
    .metric-card:hover {
        box-shadow: var(--shadow-sm);
    }
    
    .metric-card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: var(--sp-sm);
    }
    
    .metric-card-label {
        font-size: 12px;
        font-weight: 500;
        line-height: 16px;
        letter-spacing: 0.02em;
        text-transform: uppercase;
        color: var(--on-surface-variant);
    }
    
    .metric-card-icon {
        color: var(--outline);
        font-size: 20px;
    }
    
    .metric-card-value {
        font-size: 48px;
        font-weight: 700;
        line-height: 56px;
        letter-spacing: -0.02em;
        color: var(--on-surface);
        font-variant-numeric: tabular-nums;
    }
    
    .metric-card-value-small {
        font-size: 20px;
        font-weight: 600;
        color: var(--on-surface-variant);
    }
    
    .metric-card-delta {
        display: flex;
        align-items: center;
        gap: 4px;
        margin-top: 4px;
    }
    
    .metric-card-delta-icon {
        font-size: 16px;
    }
    
    .metric-card-delta-positive {
        color: var(--secondary);
    }
    
    .metric-card-delta-neutral {
        color: var(--outline);
    }
    
    .metric-card-delta-text {
        font-size: 14px;
        line-height: 20px;
    }
    
    .metric-badge {
        background-color: var(--secondary-container);
        color: var(--on-secondary);
        font-size: 12px;
        font-weight: 500;
        padding: 2px 8px;
        border-radius: 4px;
        display: inline-block;
    }
    
    /* ═══════════════════════════════════════════════════════════════
       SECTION CARD (Large Cards)
       ═══════════════════════════════════════════════════════════════ */
    .section-card {
        background-color: var(--surface-container-lowest);
        border: 1px solid rgba(193, 200, 194, 0.3);
        border-radius: var(--radius);
        overflow: hidden;
        height: 100%;
        display: flex;
        flex-direction: column;
    }
    
    .section-card-header {
        padding: var(--sp-md);
        border-bottom: 1px solid rgba(193, 200, 194, 0.2);
        display: flex;
        justify-between: center;
        align-items: center;
    }
    
    .section-card-header-primary {
        background-color: var(--primary-container);
        color: var(--on-primary);
    }
    
    .section-card-title {
        font-size: 20px;
        font-weight: 600;
        line-height: 28px;
        color: var(--primary-container);
    }
    
    .section-card-title-white {
        color: var(--on-primary);
    }
    
    .section-card-body {
        padding: var(--sp-md);
        flex: 1;
        display: flex;
        flex-direction: column;
    }
    
    /* ═══════════════════════════════════════════════════════════════
       DATA TABLE
       ═══════════════════════════════════════════════════════════════ */
    .data-table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: var(--sp-sm);
        font-variant-numeric: tabular-nums;
    }
    
    .data-table thead {
        background-color: var(--primary-container);
        color: var(--on-primary);
    }
    
    .data-table th {
        padding: var(--sp-sm);
        text-align: left;
        font-size: 12px;
        font-weight: 500;
        line-height: 16px;
    }
    
    .data-table th.text-right {
        text-align: right;
    }
    
    .data-table tbody tr {
        border-bottom: 1px solid rgba(193, 200, 194, 0.1);
        transition: background-color 0.1s ease;
    }
    
    .data-table tbody tr:hover {
        background-color: rgba(1, 45, 29, 0.02);
    }
    
    .data-table tbody tr:nth-child(even) {
        background-color: rgba(1, 45, 29, 0.01);
    }
    
    .data-table td {
        padding: var(--sp-sm);
        font-size: 14px;
        line-height: 20px;
        color: var(--on-surface);
    }
    
    .data-table td.text-right {
        text-align: right;
    }
    
    .data-table td.text-error {
        color: var(--error);
        font-weight: 700;
    }
    
    /* ═══════════════════════════════════════════════════════════════
       PHASE STAT BOXES
       ═══════════════════════════════════════════════════════════════ */
    .phase-box {
        background-color: var(--surface-container-low);
        border: 1px solid rgba(193, 200, 194, 0.2);
        border-radius: var(--radius);
        padding: var(--sp-sm);
        text-align: center;
    }
    
    .phase-box-error {
        background-color: rgba(255, 218, 214, 0.2);
        border: 1px solid rgba(186, 26, 26, 0.2);
    }
    
    .phase-box-label {
        font-size: 12px;
        font-weight: 500;
        line-height: 16px;
        color: var(--on-surface-variant);
        margin-bottom: 4px;
    }
    
    .phase-box-label-error {
        color: var(--error);
    }
    
    .phase-box-value {
        font-size: 24px;
        font-weight: 600;
        line-height: 32px;
        font-variant-numeric: tabular-nums;
        color: var(--on-surface);
    }
    
    .phase-box-value-error {
        color: var(--error);
    }
    
    /* ═══════════════════════════════════════════════════════════════
       CHART PLACEHOLDER
       ═══════════════════════════════════════════════════════════════ */
    .chart-placeholder {
        min-height: 300px;
        background-color: rgba(248, 249, 250, 0.5);
        background-image: 
            linear-gradient(to right, #e1e3e4 1px, transparent 1px),
            linear-gradient(to bottom, #e1e3e4 1px, transparent 1px);
        background-size: 24px 24px;
        border-radius: var(--radius);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-center;
        text-align: center;
        padding: var(--sp-md);
        margin-bottom: var(--sp-sm);
        position: relative;
        overflow: hidden;
    }
    
    .chart-placeholder-icon {
        font-size: 48px;
        color: var(--outline);
        margin-bottom: var(--sp-sm);
    }
    
    .chart-placeholder-text {
        font-size: 16px;
        line-height: 24px;
        color: var(--on-surface-variant);
    }
    
    /* ═══════════════════════════════════════════════════════════════
       INSIGHT BOX (Bottom of cards)
       ═══════════════════════════════════════════════════════════════ */
    .insight-box {
        background-color: rgba(225, 227, 228, 0.2);
        border-radius: var(--radius);
        padding: var(--sp-sm);
        text-align: center;
        font-size: 14px;
        line-height: 20px;
        color: var(--on-surface-variant);
    }
    
    /* ═══════════════════════════════════════════════════════════════
       TACTICAL DIRECTIVE BOX
       ═══════════════════════════════════════════════════════════════ */
    .tactical-box {
        background-color: var(--surface-container-low);
        padding: var(--sp-sm);
        border-left: 4px solid;
        border-radius: 0 var(--radius) var(--radius) 0;
        margin-bottom: var(--sp-sm);
    }
    
    .tactical-box-error {
        border-left-color: var(--error);
    }
    
    .tactical-box-success {
        border-left-color: var(--secondary);
    }
    
    .tactical-box-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 4px;
    }
    
    .tactical-box-title {
        font-size: 14px;
        font-weight: 600;
        line-height: 20px;
    }
    
    .tactical-box-title-error {
        color: var(--error);
    }
    
    .tactical-box-title-success {
        color: var(--secondary);
    }
    
    .tactical-box-badge {
        font-size: 12px;
        font-weight: 500;
        padding: 1px 8px;
        border-radius: 4px;
    }
    
    .tactical-box-badge-error {
        background-color: rgba(186, 26, 26, 0.1);
        color: var(--error);
    }
    
    .tactical-box-body {
        font-size: 14px;
        line-height: 20px;
        color: var(--on-surface);
    }
    
    /* ═══════════════════════════════════════════════════════════════
       STREAMLIT OVERRIDES
       ═══════════════════════════════════════════════════════════════ */
    
    /* Columns with no gap */
    div[data-testid="column"] {
        padding: 0 8px !important;
    }
    
    div[data-testid="column"]:first-child {
        padding-left: 0 !important;
    }
    
    div[data-testid="column"]:last-child {
        padding-right: 0 !important;
    }
    
    /* Remove extra space from markdown */
    .stMarkdown {
        margin-bottom: 0 !important;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: var(--surface-container) !important;
        border-right: 1px solid rgba(193, 200, 194, 0.3) !important;
    }
    
    [data-testid="stSidebar"] .sidebar-brand {
        padding: var(--sp-md);
        margin-bottom: var(--sp-md);
    }
    
    [data-testid="stSidebar"] .sidebar-brand h2 {
        font-size: 20px !important;
        font-weight: 600 !important;
        color: var(--primary) !important;
        margin: 0 !important;
    }
    
    [data-testid="stSidebar"] .sidebar-brand p {
        font-size: 14px !important;
        color: var(--on-surface-variant) !important;
        margin: 0 !important;
    }
    
    /* Sidebar buttons */
    [data-testid="stSidebar"] button {
        border-radius: var(--radius) !important;
        font-size: 14px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
    }
    
    [data-testid="stSidebar"] button[kind="primary"] {
        background-color: var(--primary-container) !important;
        color: var(--on-primary) !important;
    }
    
    [data-testid="stSidebar"] button[kind="secondary"] {
        background-color: transparent !important;
        color: var(--on-surface-variant) !important;
    }
    
    [data-testid="stSidebar"] button[kind="secondary"]:hover {
        background-color: rgba(174, 238, 203, 0.2) !important;
        color: var(--on-surface) !important;
    }
    
    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    
    ::-webkit-scrollbar-track {
        background: transparent;
    }
    
    ::-webkit-scrollbar-thumb {
        background: var(--outline-variant);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: var(--outline);
    }
    
</style>
"""
