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
        --surface: #f4f7f5;
        --surface-2: #ffffff;
        --surface-3: #edf2ef;
        --surface-container-lowest: #ffffff;
        --surface-container-low: #edf2ef;
        --surface-container: #e3ebe6;
        --primary: #103b2f;
        --primary-2: #18503f;
        --on-primary: #ffffff;
        --on-primary-container: #d6eadf;
        --secondary: #b7802f;
        --secondary-soft: #f6e5c8;
        --secondary-container: #f6e5c8;
        --on-secondary: #5a3d0e;
        --error: #b42318;
        --on-surface: #17231f;
        --on-surface-variant: #4a5a54;
        --outline: #7d8f88;
        --outline-2: #cad4cf;
        --outline-variant: #cad4cf;
        --border-subtle: #d9e2dd;
        --radius: 14px;
        --shadow: 0 10px 24px rgba(12, 36, 28, 0.06);
    }

    * {
        font-family: "IBM Plex Sans", "Segoe UI", sans-serif !important;
    }

    h1, h2, h3, h4, .page-title, .jb-brand-title {
        font-family: "Manrope", "Segoe UI", sans-serif !important;
    }

    #MainMenu, header {
        visibility: hidden;
    }

    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(circle at 15% 10%, rgba(183, 128, 47, 0.10), transparent 32%),
            radial-gradient(circle at 90% 0%, rgba(16, 59, 47, 0.12), transparent 36%),
            var(--surface);
        color: var(--on-surface);
    }

    [data-testid="stMainBlockContainer"] {
        padding-top: 1.2rem;
        max-width: 1400px;
    }

    .jb-topbar {
        background: linear-gradient(135deg, var(--primary), var(--primary-2));
        color: #ffffff;
        border-radius: 18px;
        padding: 18px 22px;
        margin-bottom: 24px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: var(--shadow);
    }

    .jb-brand-kicker {
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        opacity: 0.85;
    }

    .jb-brand-title {
        margin-top: 3px;
        font-size: 24px;
        font-weight: 800;
        letter-spacing: -0.01em;
    }

    .jb-date-pill {
        background: rgba(255, 255, 255, 0.16);
        border: 1px solid rgba(255, 255, 255, 0.28);
        padding: 8px 12px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 600;
    }

    .jb-page-head {
        margin-bottom: 18px;
    }

    .page-title {
        font-size: 30px;
        line-height: 1.1;
        letter-spacing: -0.02em;
        color: var(--on-surface);
        margin: 0;
    }

    .page-subtitle {
        margin-top: 8px;
        color: var(--on-surface-variant);
        font-size: 15px;
    }

    .insight-alert {
        background: linear-gradient(135deg, rgba(180, 35, 24, 0.08), rgba(180, 35, 24, 0.03));
        border: 1px solid rgba(180, 35, 24, 0.24);
        border-radius: var(--radius);
        padding: 12px 14px;
        margin-top: 14px;
        display: flex;
        gap: 10px;
    }

    .insight-alert-text {
        color: var(--on-surface);
        font-size: 14px;
    }

    .insight-label {
        font-weight: 700;
    }

    .card, .metric-card, .section-card {
        background: var(--surface-2);
        border: 1px solid var(--outline-2);
        border-radius: var(--radius);
        box-shadow: var(--shadow);
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
        padding: 16px;
        min-height: 148px;
    }

    .metric-card-label {
        font-size: 11px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--on-surface-variant);
        font-weight: 700;
    }

    .metric-card-value {
        margin-top: 8px;
        font-size: 36px;
        line-height: 1;
        font-weight: 800;
        color: var(--primary);
        font-variant-numeric: tabular-nums;
    }

    .metric-card-value-small {
        font-size: 18px;
        color: var(--on-surface-variant);
        font-weight: 600;
    }

    .metric-card-delta {
        margin-top: 8px;
        font-size: 13px;
        font-weight: 600;
    }

    .metric-card-delta-positive { color: #157347; }
    .metric-card-delta-neutral { color: var(--on-surface-variant); }

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
    }

    .bolts-table th, .data-table th {
        background: var(--primary);
        color: #fff;
        font-size: 12px;
        font-weight: 700;
        padding: 10px;
        text-align: left;
        letter-spacing: 0.03em;
    }

    .bolts-table td, .data-table td {
        padding: 10px;
        border-bottom: 1px solid var(--outline-2);
        font-size: 13px;
        color: var(--on-surface);
    }

    .bolts-table tbody tr:nth-child(even), .data-table tbody tr:nth-child(even) {
        background: rgba(16, 59, 47, 0.02);
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
    }

    [data-testid="stSidebar"] .sidebar-brand {
        background: linear-gradient(135deg, var(--primary), var(--primary-2));
        color: #fff;
        border-radius: 12px;
        padding: 14px;
        margin-bottom: 12px;
    }

    [data-testid="stSidebar"] .sidebar-brand h1 {
        font-size: 18px !important;
        margin: 0 !important;
        color: #fff !important;
        font-weight: 800 !important;
    }

    [data-testid="stSidebar"] .sidebar-brand p {
        font-size: 12px !important;
        margin: 2px 0 0 !important;
        color: rgba(255,255,255,0.82) !important;
    }

    [data-testid="stSidebar"] button {
        border-radius: 10px !important;
        border: 1px solid var(--outline-2) !important;
        font-weight: 600 !important;
        min-height: 40px;
    }

    [data-testid="stSidebar"] button[kind="primary"] {
        background: var(--primary) !important;
        border-color: var(--primary) !important;
        color: #fff !important;
    }

    [data-testid="stSidebar"] button[kind="secondary"] {
        background: #fff !important;
        color: var(--on-surface) !important;
    }

    .stButton button {
        border-radius: 10px !important;
        font-weight: 600 !important;
    }

    @media (max-width: 1100px) {
        .jb-topbar {
            flex-direction: column;
            align-items: flex-start;
            gap: 8px;
        }
    }
</style>
"""
