"""
Win Probability Model — CricNepal Analytics Module
Predicts the probability of the batting team winning at any delivery state.
Calculates Win Probability Added (WPA) per player.

PERSPECTIVE (plan 4.3 decision, 2026-10-29): p_win is, in BOTH
innings, the probability that the team currently batting wins the
match. That is one consistent definition; the referent team changes
at the innings break by construction, so the curve's subject flips
there — displays must (and do) label it "batting team win
probability". The fixed-referent transform (probability that the
innings-1 batting team wins: p_win in innings 1, 1 - p_win in
innings 2) is exported as p_first_team_win so the whole-match
identities of master-prompt Section 5 can be checked exactly.

PRODUCTION CONSTRUCTION (plan 4.2): the shipped exports are built by
compute_and_export_wpa_oos — walk-forward by match, every match
scored by a model trained only on matches played on strictly earlier
dates. The legacy compute_and_export_wpa (train and score on the
same deliveries) is retained for reproducibility of historical
artefacts only and is NOT what the pipeline runs.
"""

import json
import tempfile
from datetime import datetime, timezone

import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.linear_model import LogisticRegression
import joblib

# Initialize logger
from src.utils.logging_config import get_logger
logger = get_logger(__name__)

try:
    from src.config.paths import NORMALIZED_DIR, EXPORT_DIR
except ImportError:
    NORMALIZED_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "normalized"
    EXPORT_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "exports"

MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

class WinProbabilityModel:
    def __init__(self):
        self.model_inn1 = LogisticRegression(C=1.0, max_iter=1000)
        self.model_inn2 = LogisticRegression(C=1.0, max_iter=1000)
        self._is_trained = False

    def build_match_states(self, bbb_df: pd.DataFrame, matches_df: pd.DataFrame) -> pd.DataFrame:
        """
        Build delivery-level features for training or prediction.
        Splits data by innings and adds target labels.
        """
        logger.info("Building match states from ball-by-ball data...")
        
        # Sort deliveries chronologically
        df = bbb_df.sort_values(['match_id', 'innings', 'over', 'ball']).copy()
        
        # Map matches to extract winners
        winner_map = matches_df.set_index('match_id')['winner_name'].to_dict()
        df['match_winner'] = df['match_id'].map(winner_map)
        
        # Target: 1 if batting team wins, 0 otherwise
        df['is_batting_team_winner'] = (df['batting_team'] == df['match_winner']).astype(int)
        
        # Calculate balls bowled and balls remaining
        # Cricket over is 0-indexed, ball is 1-indexed (normally 1 to 6)
        df['balls_bowled'] = df['over'] * 6 + df['ball'].clip(1, 6)
        df['balls_remaining'] = (120 - df['balls_bowled']).clip(0, 120)
        
        # Cumulative runs scored by the batting team in the innings
        df['runs_cumulative'] = df.groupby(['match_id', 'innings'])['runs_total'].cumsum()
        
        # Cumulative wickets fallen in the innings
        df['wickets_cumulative'] = df.groupby(['match_id', 'innings'])['is_wicket'].cumsum()
        
        # Get total score of Innings 1 to determine targets for Innings 2
        inn1_scores = df[df['innings'] == 1].groupby('match_id')['runs_total'].sum().to_dict()
        df['inn1_total'] = df['match_id'].map(inn1_scores)
        
        # Innings 2 target runs and required runs
        df['target_runs'] = df['inn1_total'] + 1
        df['runs_required'] = (df['target_runs'] - df['runs_cumulative']).clip(0)
        
        # Required run rate (RRR)
        df['required_run_rate'] = np.where(
            df['balls_remaining'] > 0,
            df['runs_required'] / (df['balls_remaining'] / 6.0),
            np.where(df['runs_required'] > 0, 99.0, 0.0)
        )
        
        # Current run rate (CRR)
        df['current_run_rate'] = np.where(
            df['balls_bowled'] > 0,
            df['runs_cumulative'] / (df['balls_bowled'] / 6.0),
            0.0
        )
        
        return df

    def train(self, bbb_df: pd.DataFrame, matches_df: pd.DataFrame):
        """Train Innings 1 and Innings 2 Logistic Regression models."""
        df = self.build_match_states(bbb_df, matches_df)
        
        # Innings 1
        df_inn1 = df[df['innings'] == 1].copy()
        X_inn1 = df_inn1[['balls_remaining', 'runs_cumulative', 'wickets_cumulative', 'current_run_rate']]
        y_inn1 = df_inn1['is_batting_team_winner']
        
        # Innings 2
        df_inn2 = df[df['innings'] == 2].copy()
        X_inn2 = df_inn2[['balls_remaining', 'runs_required', 'wickets_cumulative', 'required_run_rate', 'current_run_rate']]
        y_inn2 = df_inn2['is_batting_team_winner']
        
        logger.info(f"Training Innings 1 model on {len(X_inn1)} rows...")
        self.model_inn1.fit(X_inn1, y_inn1)
        
        logger.info(f"Training Innings 2 model on {len(X_inn2)} rows...")
        self.model_inn2.fit(X_inn2, y_inn2)
        
        self._is_trained = True
        logger.info("Win Probability Models trained successfully.")
        
        # Save models
        joblib.dump(self.model_inn1, MODEL_DIR / "win_probability_inn1.joblib")
        joblib.dump(self.model_inn2, MODEL_DIR / "win_probability_inn2.joblib")
        logger.info(f"Models saved to {MODEL_DIR}")

    def predict_delivery_probs(self, states_df: pd.DataFrame) -> pd.Series:
        """Predict win probabilities for a dataframe of match states."""
        if not self._is_trained:
            # Try to load models
            inn1_path = MODEL_DIR / "win_probability_inn1.joblib"
            inn2_path = MODEL_DIR / "win_probability_inn2.joblib"
            if inn1_path.exists() and inn2_path.exists():
                self.model_inn1 = joblib.load(inn1_path)
                self.model_inn2 = joblib.load(inn2_path)
                self._is_trained = True
            else:
                raise ValueError("Model is not trained and saved models not found.")
                
        probs = np.zeros(len(states_df))
        
        # Innings 1 predictions
        mask_inn1 = states_df['innings'] == 1
        if mask_inn1.any():
            X_inn1 = states_df.loc[mask_inn1, ['balls_remaining', 'runs_cumulative', 'wickets_cumulative', 'current_run_rate']]
            probs[mask_inn1] = self.model_inn1.predict_proba(X_inn1)[:, 1]
            
        # Innings 2 predictions
        mask_inn2 = states_df['innings'] == 2
        if mask_inn2.any():
            X_inn2 = states_df.loc[mask_inn2, ['balls_remaining', 'runs_required', 'wickets_cumulative', 'required_run_rate', 'current_run_rate']]
            probs[mask_inn2] = self.model_inn2.predict_proba(X_inn2)[:, 1]
            
        return pd.Series(probs, index=states_df.index)


def _force_decided_states(states: pd.DataFrame) -> pd.DataFrame:
    """Force innings-2 probabilities at decided states to the outcome.

    Once a chase is mathematically decided, P(batting team wins) is
    not a model estimate: target reached -> exactly 1.0; balls or
    wickets exhausted with runs still required -> exactly 0.0 (a tie
    is not a win for the batting team). Applied after prediction,
    before WPA is chained (criteria P4).
    """
    states = states.copy()
    inn2 = states['innings'] == 2
    won = inn2 & (states['runs_required'] <= 0)
    lost = inn2 & (states['runs_required'] > 0) & (
        (states['balls_remaining'] <= 0) | (states['wickets_cumulative'] >= 10))
    states.loc[won, 'p_win'] = 1.0
    states.loc[lost, 'p_win'] = 0.0
    return states


def add_wpa_columns(states: pd.DataFrame) -> pd.DataFrame:
    """Chain WPA onto states that already carry p_win.

    Baselines (criteria P3): innings 1 opens at the neutral pre-match
    prior 0.50. Innings 2 opens at 1 - (final p_win of innings 1):
    under the batting-team perspective that is exactly the chasing
    team's win probability at the start of the chase, i.e. the chain
    is continuous. (The pre-2026-10 code filled every first ball with
    0.50 while its comment claimed innings 2 inherited innings 1 —
    audit R1.)

    Telescoping (criteria P5), exact by construction:
      sum(wpa_batting, innings 1) = final p_win(inn1) - 0.50
      sum(wpa_batting, innings 2) = outcome - (1 - final p_win(inn1))
    and on the fixed-referent chain,
      sum(wpa_first_team, match)  = outcome(first-innings team) - 0.50.
    """
    states = states.sort_values(
        ['match_id', 'innings', 'over', 'ball']).copy()
    states['p_first_team_win'] = np.where(
        states['innings'] == 1, states['p_win'], 1.0 - states['p_win'])

    grp = states.groupby(['match_id', 'innings'])
    states['prev_p_win'] = grp['p_win'].shift(1)
    inn1_final = (states[states['innings'] == 1]
                  .groupby('match_id')['p_win'].last())
    first_inn2 = (states['innings'] == 2) & states['prev_p_win'].isna()
    states.loc[first_inn2, 'prev_p_win'] = (
        1.0 - states.loc[first_inn2, 'match_id'].map(inn1_final))
    states['prev_p_win'] = states['prev_p_win'].fillna(0.50)
    states['wpa_batting'] = states['p_win'] - states['prev_p_win']
    states['wpa_bowling'] = -states['wpa_batting']

    states['prev_p_first_team'] = states.groupby('match_id')[
        'p_first_team_win'].shift(1)
    states['prev_p_first_team'] = states['prev_p_first_team'].fillna(0.50)
    states['wpa_first_team'] = (states['p_first_team_win']
                                - states['prev_p_first_team'])
    return states


def predict_walk_forward(deliveries: pd.DataFrame, matches: pd.DataFrame,
                         min_train_matches: int = 4,
                         match_ids=None) -> pd.DataFrame:
    """Out-of-sample delivery states with p_win (plan 4.2).

    Every scored match is predicted by a model trained ONLY on
    matches played on strictly earlier dates (same-date matches never
    train each other). A match whose date has fewer than
    min_train_matches earlier matches is not scored — its probability
    stays missing rather than being filled from a model that has seen
    it. Deterministic: fixed data order, deterministic solver.
    """
    matches = matches.copy()
    matches['match_date'] = pd.to_datetime(matches['match_date'],
                                           errors='coerce')
    dated = matches.dropna(subset=['match_date'])
    if len(dated) < len(matches):
        logger.warning(
            f"predict_walk_forward: {len(matches) - len(dated)} matches "
            "have no usable match_date and cannot be scored")
    date_of = dated.set_index('match_id')['match_date']
    targets = (dated if match_ids is None
               else dated[dated['match_id'].isin(match_ids)])
    scored = []
    global MODEL_DIR
    original_model_dir = MODEL_DIR
    with tempfile.TemporaryDirectory() as td:
        MODEL_DIR = Path(td)  # train() dumps joblibs; keep them ephemeral
        try:
            for date, day in targets.groupby('match_date'):
                train_ids = set(dated.loc[dated['match_date'] < date,
                                          'match_id'])
                if len(train_ids) < min_train_matches:
                    logger.info(
                        f"walk-forward: skipping {list(day['match_id'])} "
                        f"({len(train_ids)} earlier matches < "
                        f"{min_train_matches})")
                    continue
                model = WinProbabilityModel()
                model.train(deliveries[deliveries['match_id'].isin(train_ids)],
                            matches[matches['match_id'].isin(train_ids)])
                day_ids = set(day['match_id'])
                states = model.build_match_states(
                    deliveries[deliveries['match_id'].isin(day_ids)],
                    matches[matches['match_id'].isin(day_ids)])
                states['p_win'] = model.predict_delivery_probs(states)
                scored.append(states)
        finally:
            MODEL_DIR = original_model_dir
    if not scored:
        return pd.DataFrame()
    out = pd.concat(scored, ignore_index=True)
    out['match_date'] = out['match_id'].map(date_of)
    return out.sort_values(
        ['match_date', 'match_id', 'innings', 'over', 'ball']
    ).reset_index(drop=True)


def _write_export_meta(export_path: Path, method: str, note: str,
                       extra: dict | None = None):
    """Sidecar provenance for an export (plan 4.4): every shipped WPA
    file carries how it was generated, in machine-readable form."""
    meta = {
        "export": export_path.name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": method,
        "note": note,
    }
    if extra:
        meta.update(extra)
    export_path.with_suffix(export_path.suffix + ".meta.json").write_text(
        json.dumps(meta, indent=1))


def _export_wpa(states: pd.DataFrame, method: str, note: str,
                extra_meta: dict | None = None):
    """Write the delivery export + player leaderboard + sidecars."""
    output_cols = [
        'match_id', 'innings', 'over', 'ball', 'batting_team', 'bowling_team',
        'batter_name', 'bowler_name', 'runs_total', 'is_wicket',
        'balls_remaining', 'runs_cumulative', 'wickets_cumulative', 'p_win',
        'p_first_team_win', 'wpa_batting',
    ]
    export_df = states[output_cols].rename(columns={'wpa_batting': 'wpa'})
    export_path = EXPORT_DIR / "win_probability_by_delivery.csv"
    export_df.to_csv(export_path, index=False)
    _write_export_meta(export_path, method, note, extra_meta)
    logger.info(f"Exported delivery-level WPA to {export_path}")

    bat_wpa = export_df.groupby('batter_name').agg(
        balls=('runs_total', 'count'),
        runs=('runs_total', 'sum'),
        total_wpa=('wpa', 'sum')
    ).reset_index().rename(columns={'batter_name': 'player_name',
                                    'total_wpa': 'batting_wpa'})
    bowl_wpa = export_df.groupby('bowler_name').agg(
        balls=('runs_total', 'count'),
        wickets=('is_wicket', 'sum'),
        total_wpa=('wpa', lambda x: -x.sum())
    ).reset_index().rename(columns={'bowler_name': 'player_name',
                                    'total_wpa': 'bowling_wpa'})
    player_wpa = pd.merge(bat_wpa, bowl_wpa, on='player_name',
                          how='outer').fillna(0)
    player_wpa['combined_wpa'] = (player_wpa['batting_wpa']
                                  + player_wpa['bowling_wpa'])
    player_wpa = player_wpa.sort_values('combined_wpa', ascending=False)
    player_wpa_path = EXPORT_DIR / "player_wpa_leaderboard.csv"
    player_wpa.to_csv(player_wpa_path, index=False)
    _write_export_meta(player_wpa_path, method, note, extra_meta)
    logger.info(f"Exported player WPA leaderboard to {player_wpa_path}")


def compute_and_export_wpa_oos(min_train_matches: int = 4):
    """Production WPA pipeline (plan 4.2/4.4): walk-forward training,
    decided states forced, correct innings-2 baseline. This is what
    refresh_all runs via main()."""
    logger.info("Starting Win Probability & WPA pipeline (walk-forward)...")
    matches_file = NORMALIZED_DIR / "matches_normalized.parquet"
    deliveries_file = NORMALIZED_DIR / "ball_by_ball_normalized.parquet"
    if not (matches_file.exists() and deliveries_file.exists()):
        logger.error(f"Normalized data not found in {NORMALIZED_DIR}")
        return
    matches = pd.read_parquet(matches_file)
    deliveries = pd.read_parquet(deliveries_file)

    states = predict_walk_forward(deliveries, matches,
                                  min_train_matches=min_train_matches)
    if states.empty:
        logger.error("walk-forward produced no scored states")
        return
    states = _force_decided_states(states)
    states = add_wpa_columns(states)
    n_matches = int(states['match_id'].nunique())
    _export_wpa(
        states,
        method="walk_forward_by_match",
        note=("Out-of-sample by construction: each match was scored by "
              "a model trained only on matches played on strictly "
              "earlier dates. p_win is P(batting team wins) in both "
              "innings; p_first_team_win is the fixed-referent chain."),
        extra_meta={"min_train_matches": min_train_matches,
                    "matches_scored": n_matches},
    )


def compute_and_export_wpa():
    """LEGACY in-sample pipeline — retained for reproducibility of
    historical artefacts only. Trains on all deliveries and scores
    the same deliveries (audit I-04); refresh_all no longer calls
    this. Its exports are stamped method=in_sample_legacy."""
    logger.info("Starting Win Probability & WPA pipeline...")
    
    matches_file = NORMALIZED_DIR / "matches_normalized.parquet"
    deliveries_file = NORMALIZED_DIR / "ball_by_ball_normalized.parquet"
    
    if not (matches_file.exists() and deliveries_file.exists()):
        logger.error(f"Normalized data not found in {NORMALIZED_DIR}")
        return
        
    matches = pd.read_parquet(matches_file)
    deliveries = pd.read_parquet(deliveries_file)
    
    # Instantiate and train model
    wp_model = WinProbabilityModel()
    wp_model.train(deliveries, matches)
    
    # Generate states and predict probabilities
    states = wp_model.build_match_states(deliveries, matches)
    states['p_win'] = wp_model.predict_delivery_probs(states)
    
    # Calculate WPA (Win Probability Added)
    # WPA is the change in win probability of the batting team from ball n-1 to ball n.
    # For bowler/fielding team, it is the negative of this value.
    states['prev_p_win'] = states.groupby(['match_id', 'innings'])['p_win'].shift(1)
    
    # For the first ball of innings 1, baseline is 0.50 (equal chance)
    # For the first ball of innings 2, baseline is the final probability of innings 1 (or 0.50 if not found)
    states['prev_p_win'] = states['prev_p_win'].fillna(0.50)
    
    states['wpa_batting'] = states['p_win'] - states['prev_p_win']
    states['wpa_bowling'] = -states['wpa_batting']
    
    # Export full delivery-level win probabilities
    output_cols = [
        'match_id', 'innings', 'over', 'ball', 'batting_team', 'bowling_team',
        'batter_name', 'bowler_name', 'runs_total', 'is_wicket',
        'balls_remaining', 'runs_cumulative', 'wickets_cumulative', 'p_win', 'wpa_batting'
    ]
    export_df = states[output_cols].rename(columns={'wpa_batting': 'wpa'})
    export_path = EXPORT_DIR / "win_probability_by_delivery.csv"
    export_df.to_csv(export_path, index=False)
    _write_export_meta(
        export_path, method="in_sample_legacy",
        note=("WARNING: legacy in-sample construction — the model was "
              "trained on the same deliveries it scored (audit I-04). "
              "Superseded by compute_and_export_wpa_oos."))
    logger.info(f"Exported delivery-level WPA to {export_path}")
    
    # --- AGGREGATE PLAYER WPA LEADERS ---
    # Batting WPA
    bat_wpa = export_df.groupby('batter_name').agg(
        balls=('runs_total', 'count'),
        runs=('runs_total', 'sum'),
        total_wpa=('wpa', 'sum')
    ).reset_index().rename(columns={'batter_name': 'player_name', 'total_wpa': 'batting_wpa'})
    
    # Bowling WPA
    bowl_wpa = export_df.groupby('bowler_name').agg(
        balls=('runs_total', 'count'),
        wickets=('is_wicket', 'sum'),
        total_wpa=('wpa', lambda x: -x.sum()) # Bowling WPA is negative of batting change
    ).reset_index().rename(columns={'bowler_name': 'player_name', 'total_wpa': 'bowling_wpa'})
    
    # Combine WPA leaderboards
    player_wpa = pd.merge(bat_wpa, bowl_wpa, on='player_name', how='outer').fillna(0)
    player_wpa['combined_wpa'] = player_wpa['batting_wpa'] + player_wpa['bowling_wpa']
    player_wpa = player_wpa.sort_values('combined_wpa', ascending=False)
    
    player_wpa_path = EXPORT_DIR / "player_wpa_leaderboard.csv"
    player_wpa.to_csv(player_wpa_path, index=False)
    _write_export_meta(
        player_wpa_path, method="in_sample_legacy",
        note=("WARNING: legacy in-sample construction — the model was "
              "trained on the same deliveries it scored (audit I-04). "
              "Superseded by compute_and_export_wpa_oos."))
    logger.info(f"Exported player WPA leaderboard to {player_wpa_path}")

def main():
    compute_and_export_wpa_oos()

if __name__ == "__main__":
    main()
