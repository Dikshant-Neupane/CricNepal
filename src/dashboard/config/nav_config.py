"""
Navigation configuration for Janakpur Bolts dashboard.
Defines the sidebar menu structure.
"""

# Main navigation items.
#
# SEASON 3 SHOWCASE MODE (2026-10-24): during the season the public app
# shows only the Season 3 layer — hub, predictions, players. The S1/S2
# analytics pages are FROZEN, not deleted: their modules and routes are
# untouched, and restoring them is moving items back from
# FROZEN_NAV_ITEMS to NAV_ITEMS.
NAV_ITEMS = [
    {"icon": "", "label": "Season 3 Hub", "key": "season3_hub"},
    {"icon": "", "label": "Match Predictions", "key": "match_predictions"},
    {"icon": "", "label": "Player Profiles", "key": "player_profiles"},
]

# Frozen for the Season 3 showcase — reachable again by moving an item
# back into NAV_ITEMS. Nothing here is deleted.
FROZEN_NAV_ITEMS = [
    {"icon": "", "label": "Dashboard", "key": "dashboard"},
    {"icon": "", "label": "Season Analysis", "key": "team_decline_analysis"},
    {"icon": "", "label": "Batting Analysis", "key": "batting_analysis"},
    {"icon": "", "label": "Bowling Analysis", "key": "bowling_analysis"},
    {"icon": "", "label": "Matchup Engine", "key": "matchup_engine"},
    {"icon": "", "label": "Opposition Reports", "key": "opposition_reports"},
    {"icon": "", "label": "Match Review", "key": "review"},
    {"icon": "", "label": "S3 Recruiting", "key": "s3_recruiting"},
    {"icon": "", "label": "S3 Strategic Analysis", "key": "s3_strategic_analysis"},
    {"icon": "", "label": "Phase & Strength", "key": "phase_analysis"},
    {"icon": "", "label": "Win Probability Model", "key": "win_probability"},
    {"icon": "", "label": "Player Archetypes", "key": "player_archetypes"},
]

# Bottom navigation items (Settings, Support)
NAV_BOTTOM = [
    {"icon": "", "label": "Settings", "key": "settings"},
    {"icon": "", "label": "Support", "key": "support"},
]
