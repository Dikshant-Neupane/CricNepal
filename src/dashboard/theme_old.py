"""
Janakpur Bolts Dashboard — Design System & Theme CSS
Translates the HTML mockup's Material 3 color palette into Streamlit-compatible CSS.
"""


def get_theme_css() -> str:
    """
    Returns the full CSS string for the Bolts dashboard theme.
    Inject via st.markdown(get_theme_css(), unsafe_allow_html=True).
    """
    return """
<style>
    /* ===== Google Fonts ===== */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* ===== CSS Custom Properties (Design Tokens) ===== */
    :root {
        /* Primary (adjusted to design doc) */
        --primary: #1B4332;
        --primary-dark: #012d1d;
        --primary-container: #1B4332;
        --on-primary: #ffffff;
        --on-primary-container: #86af99;

        /* Secondary */
        --secondary: #2D6A4F;
        --secondary-container: #aeeecb;
        --on-secondary: #ffffff;
        --on-secondary-container: #316e52;

        /* Accent */
        --accent: #52B788;

        /* Error */
        --error: #ba1a1a;
        --error-container: #ffdad6;
        --on-error: #ffffff;

        /* Surface */
        --surface: #F8F9FA;
        --surface-container: #edeeef;
        --surface-container-low: #f3f4f5;
        --surface-container-high: #e7e8e9;
        --surface-container-lowest: #ffffff;
        --surface-variant: #e1e3e4;
        --on-surface: #191c1d;
        --on-surface-variant: #414844;

        /* Outline */
        --outline: #717973;
        --outline-variant: #c1c8c2;
        --border-subtle: rgba(27, 67, 50, 0.1); /* 10% primary green */

        /* Elevations */
        --elevation-1: 0 2px 8px rgba(0, 0, 0, 0.04);
        
        /* Spacing */
        --sp-xs: 4px;
        --sp-base: 8px;
        --sp-sm: 12px;
        --sp-gutter: 16px;
        --sp-md: 24px;
        --sp-lg: 48px;
        --sp-xl: 64px;
    }

    /* ===== Global Resets ===== */
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        background-color: var(--surface) !important;
        color: var(--on-surface) !important;
    }

    /* ===== Scrollbar ===== */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: var(--outline-variant); border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: var(--outline); }

    /* ===== Sidebar ===== */
    [data-testid="stSidebar"] {
        background: var(--surface) !important;
        border-right: 1px solid var(--border-subtle) !important;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: var(--on-surface) !important;
    }
    [data-testid="stSidebar"] hr {
        border-color: var(--outline-variant) !important;
    }

    /* Sidebar brand */
    .sidebar-brand {
        padding: 16px 8px 12px 8px;
        border-bottom: 1px solid var(--outline-variant);
        margin-bottom: 16px;
    }
    .sidebar-brand h1 {
        font-size: 20px !important;
        font-weight: 700 !important;
        color: var(--primary) !important;
        margin: 0 !important;
        line-height: 28px;
    }
    .sidebar-brand p {
        font-size: 12px !important;
        color: var(--on-surface-variant) !important;
        margin: 2px 0 0 0 !important;
        letter-spacing: 0.02em;
        font-weight: 500;
    }

    /* Sidebar nav links */
    .nav-item {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 10px 14px;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 600;
        letter-spacing: 0.01em;
        color: var(--on-surface-variant);
        text-decoration: none;
        cursor: pointer;
        transition: all 0.15s ease;
        margin: 2px 0;
    }
    .nav-item:hover {
        background: rgba(174, 238, 203, 0.35);
        color: var(--on-surface);
    }
    .nav-item.active {
        background: var(--primary-container);
        color: var(--on-primary) !important;
        font-weight: 700;
    }
    .nav-icon { font-size: 18px; width: 22px; text-align: center; }

    /* ===== Header Bar ===== */
    header[data-testid="stHeader"] {
        background: var(--surface) !important;
        border-bottom: 1px solid var(--outline-variant);
    }
    .top-header {
        font-size: 24px;
        font-weight: 700;
        color: var(--primary);
        line-height: 32px;
        padding: 12px 0 8px 0;
    }

    /* ===== Page Headers ===== */
    .page-title {
        font-size: 32px;
        font-weight: 600;
        color: var(--on-surface);
        line-height: 40px;
        letter-spacing: -0.01em;
        margin: 0;
    }
    .page-subtitle {
        font-size: 16px;
        font-weight: 400;
        color: var(--on-surface-variant);
        line-height: 24px;
        margin: 4px 0 0 0;
    }

    /* ===== Section Headers ===== */
    .section-header {
        font-size: 20px;
        font-weight: 600;
        line-height: 28px;
        color: var(--on-surface);
        margin: 0;
    }
    .section-header-bar {
        background: var(--primary-container);
        color: var(--on-primary);
        padding: 10px 24px;
        border-radius: 8px 8px 0 0;
        border-bottom: 1px solid var(--primary);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .section-header-bar h3 {
        font-size: 20px;
        font-weight: 600;
        margin: 0;
        color: var(--on-primary);
    }
    .section-header-bar .icon {
        font-size: 22px;
        opacity: 0.8;
    }

    /* ===== Metric Cards ===== */
    .metric-card-bolts {
        background: var(--surface-container-lowest);
        border: 1px solid var(--border-subtle);
        border-radius: 8px;
        padding: 24px;
        transition: box-shadow 0.2s ease;
    }
    .metric-card-bolts:hover {
        box-shadow: var(--elevation-1);
    }
    .metric-label {
        font-size: 12px;
        font-weight: 500;
        color: var(--on-surface-variant);
        text-transform: uppercase;
        letter-spacing: 0.02em;
        margin: 0 0 16px 0;
    }
    .metric-value {
        font-size: 48px;
        font-weight: 700;
        color: var(--primary);
        line-height: 56px;
        letter-spacing: -0.02em;
        font-variant-numeric: tabular-nums;
    }
    .metric-delta {
        font-size: 14px;
        font-weight: 500;
        line-height: 20px;
        margin-left: 10px;
    }
    .metric-delta.positive { color: var(--accent); }
    .metric-delta.negative { color: var(--error); }
    .metric-delta.neutral { color: var(--on-surface-variant); }
    .metric-desc {
        font-size: 14px;
        color: var(--on-surface-variant);
        margin: 12px 0 0 0;
        padding-top: 12px;
        border-top: 1px solid var(--surface-variant);
        line-height: 20px;
    }

    /* ===== Phase Cards ===== */
    .phase-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 16px;
        padding: 24px;
        background: rgba(45, 106, 79, 0.05); /* 5% secondary green depth */
    }
    .phase-card {
        background: var(--surface-container-lowest);
        border: 1px solid var(--border-subtle);
        border-radius: 8px;
        padding: 12px;
    }
    .phase-card.highlight-secondary {
        background: rgba(82, 183, 136, 0.05); /* Accent highlight */
        border-color: var(--accent);
    }
    .phase-card.highlight-error {
        background: rgba(186, 26, 26, 0.05);
        border-color: rgba(186, 26, 26, 0.2);
    }
    .phase-title {
        font-size: 12px;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.02em;
        color: var(--on-surface-variant);
        padding-bottom: 6px;
        border-bottom: 1px solid var(--border-subtle);
        margin-bottom: 8px;
    }
    .phase-title.secondary { color: var(--accent); border-color: rgba(82,183,136,0.2); }
    .phase-title.error { color: var(--error); border-color: rgba(186,26,26,0.2); }
    .phase-stat-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px 0;
    }
    .phase-stat-label {
        font-size: 12px;
        font-weight: 500;
        color: var(--on-surface-variant);
        letter-spacing: 0.02em;
    }
    .phase-stat-value {
        font-size: 14px;
        font-weight: 600;
        color: var(--primary);
        font-variant-numeric: tabular-nums;
    }
    .phase-stat-value.normal { color: var(--on-surface); }
    .phase-stat-value.accent { color: var(--accent); font-weight: 700; }
    .phase-stat-value.error { color: var(--error); font-weight: 600; }

    /* ===== Bar Chart (Order Contribution) ===== */
    .bar-row {
        display: flex;
        align-items: center;
        margin-bottom: 12px;
    }
    .bar-label {
        width: 64px;
        font-size: 12px;
        font-weight: 500;
        color: var(--on-surface-variant);
        letter-spacing: 0.02em;
    }
    .bar-track {
        flex: 1;
        height: 24px;
        background: var(--surface-container);
        border-radius: 9999px;
        overflow: hidden;
    }
    .bar-fill {
        height: 100%;
        border-radius: 9999px;
        transition: width 0.6s ease;
    }
    .bar-fill.primary { background: var(--primary); }
    .bar-fill.secondary { background: var(--secondary); }
    .bar-fill.tertiary { background: var(--accent); }
    .bar-fill.muted { background: var(--outline-variant); }
    .bar-value {
        width: 48px;
        text-align: right;
        font-size: 14px;
        font-weight: 600;
        font-variant-numeric: tabular-nums;
    }

    /* ===== Match Summary Card ===== */
    .match-summary-header {
        padding: 24px;
        border-bottom: 1px solid var(--outline-variant);
        background: rgba(44, 105, 78, 0.05);
        border-radius: 8px 8px 0 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .match-summary-header h3 {
        font-size: 20px;
        font-weight: 600;
        color: var(--primary);
        margin: 0;
    }
    .result-badge {
        background: var(--primary-container);
        color: var(--on-primary);
        padding: 4px 12px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: 500;
        letter-spacing: 0.02em;
    }
    .score-display {
        font-size: 48px;
        font-weight: 700;
        line-height: 56px;
        letter-spacing: -0.02em;
    }
    .score-team-name {
        font-size: 24px;
        font-weight: 600;
        line-height: 32px;
        margin-bottom: 4px;
    }
    .score-details {
        font-size: 14px;
        color: var(--on-surface-variant);
        line-height: 20px;
    }

    /* ===== Takeaway List ===== */
    .takeaway-item {
        display: flex;
        gap: 12px;
        align-items: flex-start;
        margin-bottom: 14px;
    }
    .takeaway-icon {
        font-size: 18px;
        margin-top: 2px;
        flex-shrink: 0;
    }
    .takeaway-icon.success { color: var(--secondary); }
    .takeaway-icon.warning { color: var(--error); }
    .takeaway-title {
        font-size: 14px;
        font-weight: 600;
        color: var(--on-surface);
        line-height: 20px;
        letter-spacing: 0.01em;
    }
    .takeaway-desc {
        font-size: 14px;
        color: var(--on-surface-variant);
        line-height: 20px;
        margin-top: 2px;
    }

    /* ===== Data Tables ===== */
    .bolts-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 14px;
    }
    .bolts-table thead tr {
        background: var(--primary-container);
        color: var(--on-primary);
    }
    .bolts-table thead th {
        padding: 10px 16px;
        font-size: 12px;
        font-weight: 500;
        letter-spacing: 0.02em;
        text-align: left;
    }
    .bolts-table thead th.right { text-align: right; }
    .bolts-table tbody td {
        padding: 10px 16px;
        border-bottom: 1px solid rgba(193, 200, 194, 0.3);
        font-variant-numeric: tabular-nums;
    }
    .bolts-table tbody td.right { text-align: right; }
    .bolts-table tbody tr:hover { background: rgba(1, 45, 29, 0.03); }
    .bolts-table tbody tr:nth-child(even) { background: rgba(1, 45, 29, 0.015); }
    .bolts-table tbody tr:nth-child(even):hover { background: rgba(1, 45, 29, 0.04); }

    .delta-positive { color: var(--secondary); font-weight: 500; }
    .delta-negative { color: var(--error); font-weight: 500; }

    /* ===== Resource Heatmap ===== */
    .heatmap-row {
        display: flex;
        align-items: center;
        height: 28px;
        margin-bottom: 2px;
    }
    .heatmap-label {
        width: 52px;
        font-size: 11px;
        font-weight: 500;
        color: var(--on-surface-variant);
        padding-right: 6px;
        text-align: right;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .heatmap-cells {
        flex: 1;
        display: flex;
        gap: 1px;
    }
    .heatmap-cell {
        flex: 1;
        height: 24px;
        border-radius: 2px;
    }

    /* ===== Card Wrapper ===== */
    .card {
        background: var(--surface-container-lowest);
        border: 1px solid var(--border-subtle);
        border-radius: 8px;
        overflow: hidden;
        transition: box-shadow 0.2s ease;
    }
    .card:hover {
        box-shadow: var(--elevation-1);
    }
    .card-header {
        padding: 12px 24px;
        border-bottom: 1px solid var(--outline-variant);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .card-header h3 {
        font-size: 20px;
        font-weight: 600;
        color: var(--on-surface);
        margin: 0;
    }
    .card-body { padding: 24px; }

    /* ===== POTM Footer ===== */
    .potm-footer {
        background: var(--surface);
        padding: 10px 24px;
        border-top: 1px solid var(--outline-variant);
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 14px;
        font-weight: 600;
        color: var(--on-surface);
    }
    .potm-footer .award { color: var(--secondary); }

    /* Streamlit Button Overrides */
    .stButton > button[kind="primary"] {
        background-color: var(--primary) !important;
        color: var(--on-primary) !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        border: none !important;
    }
    .stButton > button[kind="secondary"] {
        background-color: transparent !important;
        color: var(--primary) !important;
        border: 1.5px solid var(--primary) !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
    
    /* Hide default metric styling for our custom cards */
    [data-testid="stMetricValue"] {
        font-family: 'Inter', sans-serif !important;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        font-family: 'Inter', sans-serif !important;
        font-weight: 600;
        font-size: 14px;
        color: var(--on-surface-variant);
    }
    .stTabs [aria-selected="true"] {
        color: var(--primary) !important;
        border-bottom-color: var(--primary) !important;
    }

    /* Plotly chart containers */
    .js-plotly-plot .plotly {
        font-family: 'Inter', sans-serif !important;
    }

    /* Footer */
    .dashboard-footer {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 0;
        margin-top: 48px;
        border-top: 1px solid var(--outline-variant);
        font-size: 12px;
        font-weight: 500;
        color: var(--on-surface-variant);
        letter-spacing: 0.02em;
    }

    /* ===== Responsive ===== */
    @media (max-width: 768px) {
        .phase-grid { grid-template-columns: 1fr; }
        .page-title { font-size: 28px; line-height: 36px; }
    }
</style>
"""


# ─── Color Palette (for Plotly charts) ───────────────────────────────
COLORS = {
    "primary": "#1B4332",
    "primary_dark": "#012d1d",
    "secondary": "#2D6A4F",
    "accent": "#52B788",
    "error": "#ba1a1a",
    "surface": "#f8f9fa",
    "on_surface": "#191c1d",
    "on_surface_variant": "#414844",
    "outline": "#717973",
    "outline_variant": "#c1c8c2",
}
