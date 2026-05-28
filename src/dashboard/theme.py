"""Unified visual theme for the Janakpur Bolts dashboard."""

COLORS = {
    "primary": "#103b2f",
    "primary_container": "#18503f",
    "secondary": "#b7802f",
    "secondary_container": "#f6e5c8",
    "error": "#b42318",
    "surface": "#f4f7f5",
    "on_surface": "#17231f",
    "on_surface_variant": "#4a5a54",
    "outline": "#7d8f88",
    "outline_variant": "#cad4cf",
}


def get_theme_css() -> str:
    return """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

    :root {
        /* Color Palette */
        --surface: #f4f7f5;
        --surface-2: #ffffff;
        --surface-3: #edf2ef;
        --surface-container-lowest: #ffffff;
        --surface-container-low: #edf2ef;
        --surface-container: #e3ebe6;
        --primary: #103b2f;
        --primary-2: #18503f;
        --primary-light: #1a6b51;
        --on-primary: #ffffff;
        --on-primary-container: #d6eadf;
        --secondary: #b7802f;
        --secondary-soft: #f6e5c8;
        --secondary-container: #f6e5c8;
        --on-secondary: #5a3d0e;
        --error: #b42318;
        --error-light: #fde8e6;
        --success: #057a55;
        --success-light: #d1f4e8;
        --warning: #f59e0b;
        --warning-light: #fef3c7;
        --on-surface: #17231f;
        --on-surface-variant: #4a5a54;
        --outline: #7d8f88;
        --outline-2: #cad4cf;
        --outline-variant: #cad4cf;
        --border-subtle: #d9e2dd;
        
        /* Spacing Scale */
        --space-xs: 4px;
        --space-sm: 8px;
        --space-md: 16px;
        --space-lg: 24px;
        --space-xl: 32px;
        --space-2xl: 48px;
        
        /* Border Radius */
        --radius-sm: 8px;
        --radius-md: 12px;
        --radius-lg: 16px;
        --radius-xl: 20px;
        
        /* Shadows */
        --shadow-sm: 0 1px 2px rgba(12, 36, 28, 0.04);
        --shadow-md: 0 4px 12px rgba(12, 36, 28, 0.06);
        --shadow-lg: 0 10px 24px rgba(12, 36, 28, 0.08);
        --shadow-xl: 0 20px 40px rgba(12, 36, 28, 0.12);
        
        /* Transitions */
        --transition-fast: 150ms cubic-bezier(0.4, 0, 0.2, 1);
        --transition-base: 250ms cubic-bezier(0.4, 0, 0.2, 1);
        --transition-slow: 350ms cubic-bezier(0.4, 0, 0.2, 1);
    }

    /* Global resets to eliminate any gaps */
    html, body, #root, .stApp {
        margin: 0 !important;
        padding: 0 !important;
        overflow-x: hidden;
    }
    
    body::before,
    body::after,
    .stApp::before,
    .stApp::after {
        display: none !important;
    }

    * {
        font-family: "IBM Plex Sans", "Segoe UI", sans-serif !important;
    }

    h1, h2, h3, h4, .page-title, .jb-brand-title {
        font-family: "Manrope", "Segoe UI", sans-serif !important;
        font-weight: 700;
        letter-spacing: -0.02em;
        line-height: 1.2;
    }
    /* Hide all Streamlit chrome: menu, deploy, status, header */
    #MainMenu, [data-testid="stDecoration"],
    [data-testid="stStatusWidget"],
    .stDeployButton, .stAppDeployButton,
    [data-testid="stHeaderActionElements"],
    [data-testid="stToolbar"],
    header[data-testid="stHeader"]::before,
    header[data-testid="stHeader"]::after,
    iframe[title="streamlit_option_menu.streamlit_option_menu"],
    [data-testid="stToolbarActions"],
    [data-testid="stHeader"] {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        height: 0 !important;
        max-height: 0 !important;
        overflow: hidden !important;
        position: absolute !important;
        z-index: -9999 !important;
    }

    header[data-testid="stHeader"] {
        background: transparent !important;
        pointer-events: none !important;
        height: 0 !important;
        min-height: 0 !important;
        max-height: 0 !important;
        overflow: hidden !important;
        margin: 0 !important;
        padding: 0 !important;
        position: absolute !important;
        top: -1000px !important;
        left: -1000px !important;
    }
    
    header[data-testid="stHeader"] *,
    header[data-testid="stHeader"] *::before,
    header[data-testid="stHeader"] *::after {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        height: 0 !important;
        max-height: 0 !important;
    }

    /* Lock sidebar open — always visible */
    [data-testid="stSidebarCollapsedControl"] {
        display: none !important;
    }
    section[data-testid="stSidebar"] {
        min-width: 220px !important;
        width: 220px !important;
        transform: none !important;
    }
    section[data-testid="stSidebar"][aria-expanded="false"] {
        min-width: 220px !important;
        width: 220px !important;
        transform: none !important;
        margin-left: 0 !important;
    }

    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(circle at 15% 10%, rgba(183, 128, 47, 0.10), transparent 32%),
            radial-gradient(circle at 90% 0%, rgba(16, 59, 47, 0.12), transparent 36%),
            var(--surface);
        color: var(--on-surface);
        margin-top: 0 !important;
        padding-top: 0 !important;
        position: relative;
        z-index: 1;
    }

    [data-testid="stMainBlockContainer"] {
        padding-top: 1.2rem;
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
        max-width: 1400px;
        position: relative;
        overflow-x: hidden;
        margin-top: 0 !important;
    }

    /* Ensure proper stacking context */
    [data-testid="stAppViewContainer"] {
        position: relative;
        z-index: 1;
    }

    /* Hide Streamlit branding elements that might interfere */
    [data-testid="stToolbar"] {
        display: none;
    }

    /* FIX: prevent topbar from being clipped by sidebar overlap */
    .jb-topbar-outer {
        margin-left: 0 !important;
        overflow: visible !important;
    }

    .jb-topbar {
        background: linear-gradient(135deg, var(--primary), var(--primary-2));
        color: #ffffff;
        border-radius: var(--radius-lg);
        padding: var(--space-lg) 22px;
        margin: 0 0 var(--space-lg) 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: var(--shadow-lg);
        transition: transform var(--transition-base), box-shadow var(--transition-base);
        position: relative;
        z-index: 10;
        width: 100%;
        box-sizing: border-box;
    }

    .jb-topbar:hover {
        transform: translateY(-1px);
        box-shadow: var(--shadow-xl);
    }

    .jb-brand-kicker {
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        opacity: 0.85;
        animation: fadeInUp 0.5s ease-out;
    }

    .jb-brand-title {
        margin-top: 3px;
        font-size: 24px;
        font-weight: 800;
        letter-spacing: -0.01em;
        animation: fadeInUp 0.5s ease-out 0.1s backwards;
    }

    .jb-date-pill {
        background: rgba(255, 255, 255, 0.16);
        border: 1px solid rgba(255, 255, 255, 0.28);
        padding: 8px 12px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 600;
        backdrop-filter: blur(8px);
        transition: all var(--transition-base);
        animation: fadeInUp 0.5s ease-out 0.2s backwards;
    }

    .jb-date-pill:hover {
        background: rgba(255, 255, 255, 0.24);
        border-color: rgba(255, 255, 255, 0.4);
    }

    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(12px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateX(-12px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }

    .jb-page-head {
        margin-bottom: var(--space-xl);
        animation: fadeInUp 0.5s ease-out;
    }

    .page-title {
        font-size: 32px;
        line-height: 1.1;
        letter-spacing: -0.02em;
        color: var(--on-surface);
        margin: 0 0 var(--space-sm) 0;
        background: linear-gradient(135deg, var(--primary), var(--primary-light));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .page-subtitle {
        margin-top: var(--space-sm);
        color: var(--on-surface-variant);
        font-size: 15px;
        line-height: 1.6;
        max-width: 800px;
    }

    .insight-alert {
        background: linear-gradient(135deg, rgba(180, 35, 24, 0.08), rgba(180, 35, 24, 0.03));
        border: 1px solid rgba(180, 35, 24, 0.24);
        border-left: 4px solid var(--error);
        border-radius: var(--radius-md);
        padding: var(--space-md);
        margin-top: var(--space-md);
        display: flex;
        gap: var(--space-md);
        transition: all var(--transition-base);
        animation: slideIn 0.4s ease-out;
    }

    .insight-alert:hover {
        border-color: var(--error);
        box-shadow: var(--shadow-md);
        transform: translateX(2px);
    }

    .insight-alert-text {
        color: var(--on-surface);
        font-size: 14px;
        line-height: 1.6;
    }

    .insight-label {
        font-weight: 700;
        color: var(--error);
    }

    /* Streamlit Info/Success/Warning/Error boxes */
    .stAlert {
        border-radius: var(--radius-md) !important;
        border-width: 1px !important;
        padding: var(--space-md) !important;
        animation: slideIn 0.3s ease-out;
    }

    [data-testid="stNotification"] {
        border-radius: var(--radius-md) !important;
        box-shadow: var(--shadow-lg) !important;
    }

    /* Loading spinner */
    .stSpinner > div {
        border-color: var(--primary) transparent transparent transparent !important;
    }

    .card, .metric-card, .section-card {
        background: var(--surface-2);
        border: 1px solid var(--outline-2);
        border-radius: var(--radius-md);
        box-shadow: var(--shadow-md);
        transition: all var(--transition-base);
        animation: fadeInUp 0.4s ease-out backwards;
    }

    .card:hover, .metric-card:hover, .section-card:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-lg);
        border-color: var(--primary);
    }

    .card-header {
        padding: 14px 18px;
        border-bottom: 1px solid var(--outline-2);
        background: linear-gradient(180deg, #fff, #f8fbf9);
        border-radius: var(--radius) var(--radius) 0 0;
    }

    .card-header h3 {
        margin: 0;
        font-size: 16px;
        color: var(--on-surface);
        font-weight: 700;
    }

    .card-body {
        padding: 16px;
    }

    .metric-card {
        padding: var(--space-lg);
        min-height: 148px;
        position: relative;
        overflow: hidden;
    }

    .metric-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 3px;
        background: linear-gradient(90deg, var(--primary), var(--primary-light));
        opacity: 0;
        transition: opacity var(--transition-base);
    }

    .metric-card:hover::before {
        opacity: 1;
    }

    .metric-card-label {
        font-size: 11px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--on-surface-variant);
        font-weight: 700;
        margin-bottom: var(--space-sm);
        display: block;
    }

    .metric-card-value {
        margin-top: var(--space-sm);
        font-size: 40px;
        line-height: 1;
        font-weight: 800;
        color: var(--primary);
        font-variant-numeric: tabular-nums;
        transition: transform var(--transition-base);
    }

    .metric-card:hover .metric-card-value {
        transform: scale(1.05);
    }

    .metric-card-value-small {
        font-size: 18px;
        color: var(--on-surface-variant);
        font-weight: 600;
    }

    .metric-card-delta {
        margin-top: var(--space-sm);
        font-size: 13px;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 4px 8px;
        border-radius: var(--radius-sm);
        transition: all var(--transition-base);
    }

    .metric-card-delta-positive {
        color: var(--success);
        background: var(--success-light);
    }
    
    .metric-card-delta-negative {
        color: var(--error);
        background: var(--error-light);
    }
    
    .metric-card-delta-neutral {
        color: var(--on-surface-variant);
        background: var(--surface-3);
    }

    .section-card { overflow: hidden; height: 100%; }
    .section-card-header { padding: 14px 16px; border-bottom: 1px solid var(--outline-2); }
    .section-card-header-primary { background: var(--primary); }
    .section-card-title { font-size: 18px; margin: 0; color: var(--on-surface); font-weight: 700; }
    .section-card-title-white { color: #fff; }
    .section-card-body { padding: 16px; }

    .chart-placeholder {
        min-height: 280px;
        border-radius: 10px;
        border: 1px dashed var(--outline);
        background: repeating-linear-gradient(
            45deg,
            rgba(16, 59, 47, 0.02),
            rgba(16, 59, 47, 0.02) 10px,
            rgba(16, 59, 47, 0.04) 10px,
            rgba(16, 59, 47, 0.04) 20px
        );
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
        padding: 14px;
    }

    .insight-box {
        background: var(--surface-3);
        border: 1px solid var(--outline-2);
        border-radius: 10px;
        padding: 10px;
        color: var(--on-surface-variant);
        font-size: 13px;
    }

    .phase-box {
        border-radius: 10px;
        border: 1px solid var(--outline-2);
        background: var(--surface-3);
        padding: 10px;
        text-align: center;
    }

    .phase-box-error {
        background: rgba(180, 35, 24, 0.08);
        border-color: rgba(180, 35, 24, 0.3);
    }

    .phase-box-label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--on-surface-variant); }
    .phase-box-value { font-size: 22px; font-weight: 700; color: var(--primary); }
    .phase-box-value-error, .phase-box-label-error { color: var(--error); }

    .bolts-table, .data-table {
        width: 100%;
        border-collapse: collapse;
        border-radius: var(--radius-md);
        overflow: hidden;
        box-shadow: var(--shadow-sm);
    }

    .bolts-table th, .data-table th {
        background: linear-gradient(135deg, var(--primary), var(--primary-light));
        color: #fff;
        font-size: 12px;
        font-weight: 700;
        padding: 12px;
        text-align: left;
        letter-spacing: 0.03em;
        text-transform: uppercase;
        position: sticky;
        top: 0;
        z-index: 10;
    }

    .bolts-table td, .data-table td {
        padding: 12px;
        border-bottom: 1px solid var(--outline-2);
        font-size: 13px;
        color: var(--on-surface);
        transition: background var(--transition-fast);
    }

    .bolts-table tbody tr:nth-child(even), .data-table tbody tr:nth-child(even) {
        background: rgba(16, 59, 47, 0.02);
    }

    .bolts-table tbody tr:hover, .data-table tbody tr:hover {
        background: var(--surface-3);
    }

    .right, .text-right { text-align: right; }
    .delta-positive { color: #157347; font-weight: 700; }
    .delta-negative { color: var(--error); font-weight: 700; }
    .text-error { color: var(--error); font-weight: 700; }

    .takeaway-item {
        display: flex;
        gap: 10px;
        padding: 10px;
        margin-bottom: 10px;
        background: #ffffff;
        border: 1px solid var(--outline-2);
        border-radius: 10px;
    }

    .takeaway-title { font-weight: 700; font-size: 13px; color: var(--on-surface); }
    .takeaway-desc { font-size: 12px; color: var(--on-surface-variant); margin-top: 2px; }
    .takeaway-icon { margin-top: 2px; }

    .mr-score-grid {
        padding: 24px;
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 32px;
        flex-wrap: wrap;
    }

    .mr-team-col {
        text-align: center;
        flex: 1;
        min-width: 180px;
    }

    .mr-vs-divider {
        text-align: center;
        padding: 0 24px;
        border-left: 1px solid rgba(193, 200, 194, 0.3);
        border-right: 1px solid rgba(193, 200, 194, 0.3);
    }

    .mr-vs-text {
        font-size: 14px;
        font-weight: 600;
        color: var(--outline);
        letter-spacing: 0.01em;
    }

    .mr-potm-group {
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .mr-potm-link {
        font-size: 12px;
        font-weight: 500;
        color: var(--primary);
        cursor: pointer;
    }

    .mr-full-height {
        height: 100%;
    }

    .mr-title-row {
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .mr-title-icon {
        font-size: 20px;
    }

    .mr-takeaway-body {
        padding: 24px;
        background: rgba(44, 105, 78, 0.05);
    }

    .mr-cell-strong {
        font-weight: 600;
    }

    .mr-cell-muted {
        color: var(--on-surface-variant);
    }

    .dashboard-footer {
        margin-top: 24px;
        padding: 12px 4px 4px;
        display: flex;
        justify-content: space-between;
        font-size: 12px;
        color: var(--on-surface-variant);
    }

    .jb-empty {
        max-width: 760px;
        background: #fff;
        border: 1px solid var(--outline-2);
        border-radius: 16px;
        padding: 34px;
        text-align: center;
    }

    .jb-empty-icon { font-size: 48px; }
    .jb-empty h3 { margin: 8px 0; color: var(--primary); }
    .jb-empty p { color: var(--on-surface-variant); }

    .jb-empty-tip {
        margin-top: 14px;
        display: inline-block;
        background: var(--secondary-soft);
        color: #6f4d15;
        border-radius: 999px;
        padding: 8px 12px;
        font-size: 12px;
        font-weight: 700;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #eff5f2, #f7faf8) !important;
        border-right: 1px solid var(--outline-2) !important;
        box-shadow: 2px 0 12px rgba(12, 36, 28, 0.04);
    }

    [data-testid="stSidebar"] .sidebar-brand {
        background: linear-gradient(135deg, var(--primary), var(--primary-2));
        color: #fff;
        border-radius: var(--radius-md);
        padding: var(--space-md);
        margin-bottom: var(--space-md);
        box-shadow: var(--shadow-md);
        transition: all var(--transition-base);
        cursor: pointer;
    }

    [data-testid="stSidebar"] .sidebar-brand:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-lg);
    }

    [data-testid="stSidebar"] .sidebar-brand h1 {
        font-size: 18px !important;
        margin: 0 !important;
        color: #fff !important;
        font-weight: 800 !important;
        letter-spacing: -0.01em;
    }

    [data-testid="stSidebar"] .sidebar-brand p {
        font-size: 12px !important;
        margin: 2px 0 0 !important;
        color: rgba(255,255,255,0.82) !important;
        font-weight: 500;
    }

    [data-testid="stSidebar"] button {
        border-radius: var(--radius-sm) !important;
        border: 1px solid var(--outline-2) !important;
        font-weight: 600 !important;
        min-height: 42px;
        transition: all var(--transition-base) !important;
        position: relative;
        overflow: hidden;
    }

    [data-testid="stSidebar"] button::before {
        content: '';
        position: absolute;
        left: 0;
        top: 0;
        height: 100%;
        width: 3px;
        background: var(--primary);
        transform: scaleY(0);
        transition: transform var(--transition-base);
    }

    [data-testid="stSidebar"] button:hover::before {
        transform: scaleY(1);
    }

    [data-testid="stSidebar"] button[kind="primary"] {
        background: var(--primary) !important;
        border-color: var(--primary) !important;
        color: #fff !important;
        box-shadow: var(--shadow-sm);
    }

    [data-testid="stSidebar"] button[kind="primary"]:hover {
        background: var(--primary-light) !important;
        transform: translateX(4px);
        box-shadow: var(--shadow-md);
    }

    [data-testid="stSidebar"] button[kind="secondary"] {
        background: #fff !important;
        color: var(--on-surface) !important;
    }

    [data-testid="stSidebar"] button[kind="secondary"]:hover {
        background: var(--surface-3) !important;
        border-color: var(--primary) !important;
        transform: translateX(2px);
    }

    .stButton button {
        border-radius: var(--radius-sm) !important;
        font-weight: 600 !important;
        padding: 10px 20px !important;
        transition: all var(--transition-base) !important;
        box-shadow: var(--shadow-sm);
    }

    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-md);
    }

    .tactical-box {
        background: var(--surface-container-low);
        border: 1px solid var(--outline-variant);
        border-radius: 10px;
        padding: 14px;
        margin-bottom: 12px;
    }

    .tactical-box-error {
        background: rgba(180, 35, 24, 0.06);
        border-color: rgba(180, 35, 24, 0.25);
    }

    .tactical-box-success {
        background: rgba(16, 59, 47, 0.06);
        border-color: rgba(16, 59, 47, 0.25);
    }

    .tactical-box-title {
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 6px;
        color: var(--on-surface-variant);
    }

    .tactical-box-title-error { color: var(--error); }
    .tactical-box-title-success { color: var(--primary); }

    .tactical-box-body {
        font-size: 13px;
        color: var(--on-surface);
        line-height: 1.5;
    }

    .metric-card-delta-negative { color: var(--error); font-weight: 600; }

    /* Chart improvements */
    .js-plotly-plot {
        border-radius: var(--radius-md);
        overflow: hidden;
    }

    /* Improved tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: var(--space-sm);
        background: var(--surface-3);
        padding: var(--space-xs);
        border-radius: var(--radius-md);
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: var(--radius-sm);
        padding: var(--space-sm) var(--space-md);
        font-weight: 600;
        transition: all var(--transition-base);
    }

    .stTabs [aria-selected="true"] {
        background: var(--primary) !important;
        color: white !important;
    }

    /* Improved selectbox/multiselect */
    .stSelectbox, .stMultiSelect {
        transition: all var(--transition-base);
    }

    [data-baseweb="select"], [data-baseweb="popover"] {
        border-radius: var(--radius-sm) !important;
    }

    /* Improved dataframe display */
    .stDataFrame {
        border-radius: var(--radius-md) !important;
        overflow: hidden;
        box-shadow: var(--shadow-sm);
    }

    /* Scrollbar styling */
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }

    ::-webkit-scrollbar-track {
        background: var(--surface-3);
        border-radius: var(--radius-sm);
    }

    ::-webkit-scrollbar-thumb {
        background: var(--outline);
        border-radius: var(--radius-sm);
        transition: background var(--transition-base);
    }

    ::-webkit-scrollbar-thumb:hover {
        background: var(--primary);
    }

    /* Loading skeleton */
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }

    .loading-skeleton {
        animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
        background: var(--surface-3);
        border-radius: var(--radius-sm);
    }

    /* Responsive Design */
    @media (max-width: 1200px) {
        .page-title {
            font-size: 28px;
        }
        .metric-card-value {
            font-size: 32px;
        }
    }

    @media (max-width: 1100px) {
        .jb-topbar {
            flex-direction: column;
            align-items: flex-start;
            gap: var(--space-sm);
        }
        .jb-brand-title {
            font-size: 20px;
        }
    }

    @media (max-width: 768px) {
        /* Main container padding */
        [data-testid="stMainBlockContainer"] {
            padding-left: var(--space-sm) !important;
            padding-right: var(--space-sm) !important;
            padding-top: var(--space-sm) !important;
        }
        
        /* Typography optimizations */
        .page-title {
            font-size: 22px !important;
            line-height: 1.3;
        }
        .page-subtitle {
            font-size: 13px;
            line-height: 1.5;
        }
        
        /* Metric cards for mobile */
        .metric-card {
            min-height: 100px;
            padding: 12px;
            margin-bottom: 8px;
        }
        .metric-card-value {
            font-size: 24px !important;
        }
        .metric-card-label {
            font-size: 10px !important;
            margin-bottom: 6px;
        }
        .metric-card-delta {
            font-size: 10px !important;
            padding: 4px 8px;
        }
        
        /* Topbar mobile optimization */
        .jb-topbar {
            padding: 12px !important;
            margin-bottom: 12px !important;
        }
        .jb-brand-title {
            font-size: 18px !important;
        }
        .jb-date-pill {
            font-size: 11px !important;
            padding: 6px 12px !important;
        }
        
        /* Page header spacing */
        .jb-page-head {
            padding: 12px 0 !important;
            margin-bottom: 16px !important;
        }
        
        /* Insight alerts */
        .insight-alert {
            padding: 12px !important;
            font-size: 12px !important;
        }
        .insight-alert-text {
            font-size: 12px !important;
        }
        
        /* Tables - horizontal scroll with better UX */
        [data-testid="stDataFrame"] {
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            max-width: 100%;
        }
        [data-testid="stDataFrame"] > div {
            min-width: 600px;
        }
        
        /* Table text sizing */
        .bolts-table, .data-table {
            font-size: 11px !important;
        }
        .bolts-table th, .data-table th {
            font-size: 10px !important;
            padding: 8px 4px !important;
            white-space: nowrap;
        }
        .bolts-table td, .data-table td {
            padding: 8px 4px !important;
        }
        
        /* Touch-optimized buttons */
        button {
            min-height: 44px !important;
            font-size: 14px !important;
            padding: 10px 16px !important;
        }
        [data-testid="stSidebar"] button {
            min-height: 42px !important;
            font-size: 13px !important;
        }
        
        /* Stack grid layouts */
        div[style*="grid-template-columns"] {
            grid-template-columns: 1fr !important;
            gap: 12px !important;
        }
        
        /* Column spacing optimization */
        [data-testid="stHorizontalBlock"] {
            gap: 4px !important;
            flex-wrap: wrap;
        }
        [data-testid="column"] {
            min-width: 0 !important;
            padding: 0 2px !important;
            flex: 1 1 auto !important;
        }
        
        /* Charts mobile optimization */
        [data-testid="stPlotlyChart"] {
            max-width: 100%;
            overflow-x: auto;
        }
        
        /* Expander mobile optimization */
        [data-testid="stExpander"] {
            margin-bottom: 12px;
        }
        [data-testid="stExpanderDetails"] {
            padding: 12px !important;
        }
        
        /* Multiselect and select boxes */
        [data-baseweb="select"] {
            font-size: 13px !important;
        }
        
        /* Reduce section spacing */
        .stMarkdown > div {
            margin-bottom: 8px !important;
        }
        
        /* Sidebar mobile adjustments */
        [data-testid="stSidebar"] {
            min-width: 260px !important;
        }
        [data-testid="stSidebar"] .sidebar-brand {
            padding: 12px !important;
        }
        [data-testid="stSidebar"] .sidebar-brand h1 {
            font-size: 16px !important;
        }
        [data-testid="stSidebar"] .sidebar-brand p {
            font-size: 11px !important;
        }
    }
    
    /* Extra small devices (phones in portrait) */
    @media (max-width: 480px) {
        .page-title {
            font-size: 20px !important;
        }
        .metric-card-value {
            font-size: 22px !important;
        }
        .jb-topbar {
            padding: 10px !important;
        }
        .jb-brand-title {
            font-size: 16px !important;
        }
        /* Force single column for KPI cards */
        [data-testid="stHorizontalBlock"]:has(.metric-card) {
            flex-direction: column !important;
        }
        [data-testid="stHorizontalBlock"]:has(.metric-card) > [data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
        }
    }
        .bolts-table td, .data-table td {
            padding: 8px 6px;
            font-size: 12px;
        }
        /* Wrap table container */
        .stDataFrame > div {
            overflow-x: auto !important;
            -webkit-overflow-scrolling: touch;
        }
    }

    @media (max-width: 480px) {
        [data-testid="stMainBlockContainer"] {
            padding-left: var(--space-xs) !important;
            padding-right: var(--space-xs) !important;
        }
        .jb-topbar {
            padding: var(--space-sm) var(--space-md);
        }
        .jb-brand-title {
            font-size: 18px;
        }
        .jb-date-pill {
            font-size: 11px;
            padding: 4px 10px;
        }
        .page-title {
            font-size: 22px;
        }
        .metric-card {
            min-height: 100px;
            padding: var(--space-sm);
        }
        .metric-card-value {
            font-size: 24px;
        }
        .metric-card-label {
            font-size: 10px;
        }
        .insight-alert {
            padding: var(--space-sm);
            font-size: 12px;
        }
        [data-testid="stSidebar"] .sidebar-brand h1 {
            font-size: 16px !important;
        }
        [data-testid="stSidebar"] .sidebar-brand p {
            font-size: 11px !important;
        }
    }

    @media (max-width: 360px) {
        .page-title {
            font-size: 20px;
        }
        .metric-card-value {
            font-size: 22px;
        }
        .jb-brand-title {
            font-size: 16px;
        }
        button {
            font-size: 13px !important;
        }
    }

    /* Print styles */
    @media print {
        [data-testid="stSidebar"],
        .jb-topbar,
        .stButton {
            display: none !important;
        }
    }

    /* Focus states for accessibility */
    button:focus-visible,
    [data-baseweb="select"]:focus-visible {
        outline: 2px solid var(--primary);
        outline-offset: 2px;
    }

    /* Smooth page transitions */
    [data-testid="stAppViewContainer"] > div {
        animation: fadeInUp 0.3s ease-out;
    }
</style>
"""
