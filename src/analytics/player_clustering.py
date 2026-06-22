"""
Player Clustering — CricNepal Analytics Module
KMeans-based role identification using batting and bowling features.
Identifies archetypes: Power Hitter, Anchor, Death Specialist, etc.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score

from src.utils.logging_config import get_logger
logger = get_logger(__name__)

try:
    from src.config.paths import NORMALIZED_DIR, EXPORT_DIR
except ImportError:
    NORMALIZED_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "normalized"
    EXPORT_DIR     = Path(__file__).resolve().parent.parent.parent / "data" / "exports"


# Archetype labels mapped by centroid characteristics
ARCHETYPE_LABELS = {
    'high_sr_low_avg':       'Power Hitter',
    'high_avg_low_sr':       'Anchor Batter',
    'balanced_bat':          'Balanced Batter',
    'low_econ_pp':           'Powerplay Specialist',
    'low_econ_death':        'Death Specialist',
    'high_wkts':             'Wicket-Taking Bowler',
    'economy_bowler':        'Economy Bowler',
    'all_rounder':           'All-Rounder',
}


def build_player_feature_matrix(bbb_df: pd.DataFrame,
                                 matches_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build a feature matrix with one row per player, combining batting
    and bowling metrics across all phases.
    """
    logger.info("Building player feature matrix...")

    df = bbb_df.merge(matches_df[['match_id', 'season']], on='match_id', how='left')

    # ── Batting features ─────────────────────────────────────────────────
    bat = df.groupby('batter_name').agg(
        bat_balls=('runs_off_bat', 'count'),
        bat_runs=('runs_off_bat', 'sum'),
        bat_boundaries=('is_boundary', 'sum'),
        bat_dots=('is_dot_ball', 'sum'),
    ).reset_index().rename(columns={'batter_name': 'player_name'})

    bat['bat_sr'] = np.where(bat['bat_balls'] > 0,
                              (bat['bat_runs'] / bat['bat_balls'] * 100).round(2), 0)
    bat['bat_boundary_pct'] = np.where(bat['bat_balls'] > 0,
                                        (bat['bat_boundaries'] / bat['bat_balls'] * 100).round(2), 0)
    bat['bat_dot_pct'] = np.where(bat['bat_balls'] > 0,
                                   (bat['bat_dots'] / bat['bat_balls'] * 100).round(2), 0)

    # ── Bowling features ─────────────────────────────────────────────────
    bowl = df.groupby('bowler_name').agg(
        bowl_balls=('runs_total', 'count'),
        bowl_runs=('runs_total', 'sum'),
        bowl_wickets=('is_wicket', 'sum'),
        bowl_dots=('is_dot_ball', 'sum'),
    ).reset_index().rename(columns={'bowler_name': 'player_name'})

    bowl['bowl_economy'] = np.where(bowl['bowl_balls'] > 0,
                                     (bowl['bowl_runs'] / (bowl['bowl_balls'] / 6)).round(2), 0)
    bowl['bowl_sr'] = np.where(bowl['bowl_wickets'] > 0,
                                (bowl['bowl_balls'] / bowl['bowl_wickets']).round(2), 999)
    bowl['bowl_dot_pct'] = np.where(bowl['bowl_balls'] > 0,
                                     (bowl['bowl_dots'] / bowl['bowl_balls'] * 100).round(2), 0)

    # ── Phase-level bowling economy ──────────────────────────────────────
    phase_bowl = df.groupby(['bowler_name', 'phase']).agg(
        phase_balls=('runs_total', 'count'),
        phase_runs=('runs_total', 'sum'),
    ).reset_index()
    phase_bowl['phase_econ'] = (phase_bowl['phase_runs'] / (phase_bowl['phase_balls'] / 6)).round(2)

    pp_econ = phase_bowl[phase_bowl['phase'] == 'Powerplay'].set_index('bowler_name')['phase_econ']
    mid_econ = phase_bowl[phase_bowl['phase'] == 'Middle'].set_index('bowler_name')['phase_econ']
    death_econ = phase_bowl[phase_bowl['phase'] == 'Death'].set_index('bowler_name')['phase_econ']

    bowl['pp_economy'] = bowl['player_name'].map(pp_econ)
    bowl['mid_economy'] = bowl['player_name'].map(mid_econ)
    bowl['death_economy'] = bowl['player_name'].map(death_econ)

    # ── Merge batting and bowling ────────────────────────────────────────
    features = pd.merge(bat, bowl, on='player_name', how='outer').fillna(0)

    # Filter to players with minimum involvement (at least 12 balls in any role)
    features = features[(features['bat_balls'] >= 12) | (features['bowl_balls'] >= 12)].copy()

    logger.info(f"Feature matrix: {len(features)} players, {len(features.columns)} features")
    return features


def cluster_players(features_df: pd.DataFrame,
                     n_clusters: int = 5) -> pd.DataFrame:
    """
    Run KMeans clustering on the player feature matrix.
    Automatically selects optimal k using silhouette score if n_clusters is None.
    """
    feature_cols = [
        'bat_sr', 'bat_boundary_pct', 'bat_dot_pct',
        'bowl_economy', 'bowl_sr', 'bowl_dot_pct',
        'pp_economy', 'mid_economy', 'death_economy',
    ]

    # Ensure all feature columns exist
    for col in feature_cols:
        if col not in features_df.columns:
            features_df[col] = 0

    X = features_df[feature_cols].fillna(0).values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Find optimal k via silhouette score
    best_k = n_clusters
    best_score = -1

    for k in range(3, min(8, len(X_scaled))):
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = km.fit_predict(X_scaled)
        if len(set(labels)) < 2:
            continue
        score = silhouette_score(X_scaled, labels)
        logger.info(f"  k={k}: silhouette={score:.3f}")
        if score > best_score:
            best_score = score
            best_k = k

    logger.info(f"Selected k={best_k} (silhouette={best_score:.3f})")

    # Final fit with best k
    km_final = KMeans(n_clusters=best_k, random_state=42, n_init=10)
    features_df = features_df.copy()
    features_df['cluster'] = km_final.fit_predict(X_scaled)

    # Label clusters by centroid characteristics
    centroids = pd.DataFrame(
        scaler.inverse_transform(km_final.cluster_centers_),
        columns=feature_cols,
    )

    cluster_labels = {}
    for idx, row in centroids.iterrows():
        # Determine dominant archetype
        if row['bat_sr'] > 130 and row['bat_boundary_pct'] > 15:
            label = 'Power Hitter'
        elif row['bat_sr'] < 110 and row['bat_dot_pct'] > 35:
            label = 'Anchor Batter'
        elif row['bowl_economy'] < 7.0 and row['bowl_sr'] < 20:
            label = 'Wicket-Taking Bowler'
        elif row['bowl_economy'] < 7.5 and row['bowl_dot_pct'] > 40:
            label = 'Economy Bowler'
        elif row['death_economy'] > 0 and row['death_economy'] < 8.0:
            label = 'Death Specialist'
        elif row['pp_economy'] > 0 and row['pp_economy'] < 6.5:
            label = 'Powerplay Specialist'
        elif row['bat_sr'] > 100 and row['bowl_economy'] > 0 and row['bowl_economy'] < 10:
            label = 'All-Rounder'
        else:
            label = f'Cluster {idx}'
        cluster_labels[idx] = label

    features_df['archetype'] = features_df['cluster'].map(cluster_labels)

    return features_df, centroids, best_score


def compute_and_export_clusters():
    """Main pipeline: build features, cluster, and export."""
    logger.info("Starting Player Clustering pipeline...")

    bbb_path = NORMALIZED_DIR / "ball_by_ball_normalized.parquet"
    mat_path = NORMALIZED_DIR / "matches_normalized.parquet"

    if not (bbb_path.exists() and mat_path.exists()):
        logger.error(f"Normalized data not found in {NORMALIZED_DIR}")
        return

    bbb = pd.read_parquet(bbb_path)
    matches = pd.read_parquet(mat_path)

    features = build_player_feature_matrix(bbb, matches)
    clustered, centroids, sil_score = cluster_players(features)

    # Export
    export_path = EXPORT_DIR / "player_archetypes.csv"
    clustered.to_csv(export_path, index=False)
    logger.info(f"Exported player archetypes to {export_path}")

    centroid_path = EXPORT_DIR / "archetype_centroids.csv"
    centroids.to_csv(centroid_path, index=False)
    logger.info(f"Exported archetype centroids to {centroid_path}")

    # Summary
    logger.info(f"Silhouette score: {sil_score:.3f}")
    logger.info(f"Archetype distribution:")
    for archetype, count in clustered['archetype'].value_counts().items():
        logger.info(f"  {archetype}: {count} players")


def main():
    compute_and_export_clusters()


if __name__ == "__main__":
    main()
