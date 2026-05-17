import importlib


MODULES = [
    "src.dashboard.app",
    "src.dashboard.services.data_quality",
    "src.dashboard.services.metrics",
    "src.dashboard.services.data_source",
    "src.dashboard.page_modules.executive_overview",
    "src.dashboard.page_modules.match_review",
    "src.dashboard.page_modules.batting_intelligence",
    "src.dashboard.page_modules.bowling_intelligence",
    "src.dashboard.page_modules.matchups",
    "src.dashboard.page_modules.opposition_report",
]


def test_dashboard_modules_importable() -> None:
    for module in MODULES:
        importlib.import_module(module)
