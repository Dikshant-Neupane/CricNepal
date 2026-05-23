"""
S3 Player Performance Forecaster
Predict S3 stats based on S1 and S2 trends.

Author: Senior Data Scientist
Date: May 21, 2026
v2.2: Composite scoring + projection-based confidence intervals
      - Trend-based predictions (rewards genuine improvers)
      - Confidence intervals: relative to prediction magnitude and volatility
      - Composite scoring: 60% wickets + 30% economy + 10% SR

Methodology Note:
    This is a heuristic projection model using domain-informed linear
    extrapolation with regression-to-mean adjustments. It is NOT a trained
    machine learning model. Confidence intervals are approximate.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')


class S3PerformanceForecaster:
    """Predict S3 player performance based on S1→S2 trends."""
    
    def __init__(self, s1_data: pd.DataFrame, s2_data: pd.DataFrame):
        """
        Initialize forecaster with S1 and S2 player stats.
        
        Args:
            s1_data: DataFrame with S1 player statistics
            s2_data: DataFrame with S2 player statistics
        """
        self.s1_data = s1_data
        self.s2_data = s2_data
        self.predictions = None
        self.validation_metrics = None
    
    def backtest_validation(self, metric_col: str = 'wickets', player_type: str = 'bowler') -> Dict:
        """
        Validate forecasting methodology by predicting S2 from S1 (if S0 data existed).
        Since we only have S1 and S2, we test on S1→S2 predictions.
        
        This is a retrospective validation: We predict S2 using only S1 data,
        then compare predictions against actual S2 outcomes.
        
        Args:
            metric_col: Column to validate ('wickets', 'economy', etc.)
            player_type: Type of player to validate ('bowler' or 'batter')
            
        Returns:
            Dictionary with MAE, RMSE, MAPE, and prediction accuracy metrics
        """
        # Filter players with both S1 and S2 data
        if player_type == 'bowler':
            players = pd.merge(
                self.s1_data[self.s1_data['role'].str.contains('bowl', case=False, na=False)],
                self.s2_data[self.s2_data['role'].str.contains('bowl', case=False, na=False)],
                on='player_name',
                suffixes=('_s1', '_s2')
            )
        else:
            players = pd.merge(
                self.s1_data[self.s1_data['role'].str.contains('bat', case=False, na=False)],
                self.s2_data[self.s2_data['role'].str.contains('bat', case=False, na=False)],
                on='player_name',
                suffixes=('_s1', '_s2')
            )
        
        # Get S1 and S2 values
        s1_col = f"{metric_col}_s1"
        s2_col = f"{metric_col}_s2"
        
        # Filter players with valid data
        valid_players = players[[s1_col, s2_col]].dropna()
        
        if len(valid_players) == 0:
            return {
                'error': 'No valid players with both S1 and S2 data',
                'n_players': 0
            }
        
        # Make predictions: Use S1 data to predict S2, assuming stable trend
        # (In reality, we'd use S0→S1 to predict S2, but we don't have S0)
        predictions = []
        actuals = []
        
        for idx, row in valid_players.iterrows():
            s1_val = row[s1_col]
            s2_actual = row[s2_col]
            
            # Simple baseline: assume continuation (S2 = S1)
            # This tests if adding complexity improves over naive baseline
            s2_pred = s1_val  # Naive forecast: no change
            
            predictions.append(s2_pred)
            actuals.append(s2_actual)
        
        predictions = np.array(predictions)
        actuals = np.array(actuals)
        
        # Calculate error metrics
        errors = actuals - predictions
        abs_errors = np.abs(errors)
        squared_errors = errors ** 2
        
        mae = np.mean(abs_errors)
        rmse = np.sqrt(np.mean(squared_errors))
        
        # MAPE (avoid division by zero)
        mape = np.mean(np.abs(errors / (actuals + 1e-10))) * 100
        
        # Directional accuracy (did we predict the right direction?)
        s1_vals = valid_players[s1_col].values
        actual_changes = actuals - s1_vals
        pred_changes = predictions - s1_vals
        
        correct_direction = np.sum(np.sign(actual_changes) == np.sign(pred_changes))
        directional_accuracy = (correct_direction / len(actuals)) * 100
        
        # Calculate baseline metrics (always predict mean)
        mean_baseline = np.mean(s1_vals)
        baseline_mae = np.mean(np.abs(actuals - mean_baseline))
        baseline_rmse = np.sqrt(np.mean((actuals - mean_baseline) ** 2))
        
        return {
            'metric': metric_col,
            'player_type': player_type,
            'n_players': len(actuals),
            'mae': round(mae, 2),
            'rmse': round(rmse, 2),
            'mape': round(mape, 1),
            'directional_accuracy': round(directional_accuracy, 1),
            'baseline_mae': round(baseline_mae, 2),
            'baseline_rmse': round(baseline_rmse, 2),
            'improvement_over_baseline': round(((baseline_mae - mae) / baseline_mae) * 100, 1)
        }
        
    def analyze_trend(self, s1_value: float, s2_value: float, metric: str) -> Dict:
        """
        Analyze trend between S1 and S2.
        
        Args:
            s1_value: S1 metric value
            s2_value: S2 metric value
            metric: Metric type ('economy', 'average', 'strike_rate', etc.)
            
        Returns:
            Dictionary with trend analysis
        """
        if pd.isna(s1_value) or pd.isna(s2_value):
            return {
                'trend': 'INSUFFICIENT_DATA',
                'delta': None,
                'pct_change': None,
                'confidence': 0
            }
        
        delta = s2_value - s1_value
        
        # Handle division by zero
        if s1_value == 0:
            pct_change = 0 if s2_value == 0 else float('inf')
        else:
            pct_change = (delta / s1_value) * 100
        
        # Classify trend based on metric type
        # NOTE: Check most extreme thresholds FIRST to avoid dead-code branches
        if metric in ['economy', 'average_against']:  # Lower is better
            if delta > 3.0:
                trend = 'CATASTROPHIC_DECLINE'
            elif delta > 1.5:
                trend = 'DECLINING'
            elif delta < -1.0:
                trend = 'IMPROVING'
            else:
                trend = 'STABLE'
        else:  # Higher is better (average, strike_rate, wickets)
            if pct_change < -80:
                trend = 'CATASTROPHIC_DECLINE'
            elif delta < -50 or pct_change < -50:
                trend = 'DECLINING'
            elif delta > 50 or pct_change > 50:
                trend = 'IMPROVING'
            else:
                trend = 'STABLE'
        
        # Calculate confidence based on sample size and consistency
        confidence = min(100, 50 + abs(pct_change) / 2)
        
        return {
            'trend': trend,
            'delta': round(delta, 2),
            'pct_change': round(pct_change, 1),
            'confidence': round(confidence, 0)
        }
    
    def predict_s3_value(self, s1_value: float, s2_value: float, 
                        trend: str) -> Tuple[float, float, float]:
        """
        Predict S3 value with confidence interval.
        
        Args:
            s1_value: S1 metric value
            s2_value: S2 metric value
            trend: Trend classification
            
        Returns:
            Tuple of (predicted_value, lower_bound, upper_bound)
        """
        if pd.isna(s1_value) or pd.isna(s2_value):
            return (None, None, None)
        
        # Simple linear extrapolation with regression to mean
        delta = s2_value - s1_value
        
        if trend == 'CATASTROPHIC_DECLINE':
            # Assume some recovery but not full (60% of delta)
            s3_pred = s2_value + (delta * -0.4)
        elif trend == 'DECLINING':
            # Assume regression to mean (50% recovery)
            s3_pred = s2_value + (delta * -0.5)
        elif trend == 'IMPROVING':
            # Assume continued improvement but slower (30% of delta)
            s3_pred = s2_value + (delta * 0.3)
        else:  # STABLE
            # Weighted average favoring recent performance
            s3_pred = (s1_value * 0.3) + (s2_value * 0.7)
        
        # Calculate confidence interval (±15% for stable, ±30% for volatile)
        if trend in ['CATASTROPHIC_DECLINE', 'IMPROVING']:
            margin = s3_pred * 0.30
        else:
            margin = s3_pred * 0.15
        
        lower_bound = s3_pred - margin
        upper_bound = s3_pred + margin
        
        return (round(s3_pred, 2), round(lower_bound, 2), round(upper_bound, 2))
    
    def calculate_composite_bowler_score(self, wkts_per_match: float, 
                                        economy: float, 
                                        bowling_sr: float) -> float:
        """
        Calculate composite bowler value score (0-100 scale).
        Weights: 60% wickets per match, 30% economy, 10% bowling strike rate
        
        Args:
            wkts_per_match: Wickets per match (normalized)
            economy: Economy rate (lower is better)
            bowling_sr: Bowling strike rate - balls per wicket (lower is better)
            
        Returns:
            Composite score (0-100)
        """
        if pd.isna(wkts_per_match) or pd.isna(economy):
            return 0
        
        # Normalize wickets per match (0-100 scale)
        # Excellent: 2.5+ wkts/match = 100, Average: 1.5 = 60, Poor: 0.5 = 20
        wickets_score = min(100, max(0, (wkts_per_match / 2.5) * 100))
        
        # Normalize economy (0-100 scale, inverted - lower is better)
        # Excellent: 6.0 economy = 100, Average: 8.0 = 50, Poor: 10.0 = 0
        economy_score = max(0, min(100, 100 - ((economy - 6.0) / 4.0) * 100))
        
        # Normalize bowling SR (0-100 scale, inverted - lower is better)
        # Excellent: 12 balls/wkt = 100, Average: 20 = 50, Poor: 28+ = 0
        if pd.isna(bowling_sr):
            sr_score = 50  # Default to average if missing
        else:
            sr_score = max(0, min(100, 100 - ((bowling_sr - 12) / 16) * 100))
        
        # Weighted composite (60% wickets, 30% economy, 10% SR)
        composite = (
            wickets_score * 0.60 +
            economy_score * 0.30 +
            sr_score * 0.10
        )
        
        return round(composite, 1)
    
    def assign_priority_from_composite(self, composite_score: float, 
                                      role: str = 'bowler') -> int:
        """
        Assign priority based on composite score.
        
        Args:
            composite_score: Composite bowler value score (0-100)
            role: Player role
            
        Returns:
            Priority level (0-10)
        """
        if pd.isna(composite_score) or composite_score == 0:
            return 0
        
        if composite_score >= 80:
            return 10  # ELITE
        elif composite_score >= 70:
            return 9   # ELITE
        elif composite_score >= 60:
            return 8   # TARGET
        elif composite_score >= 50:
            return 7   # PRIORITY
        elif composite_score >= 40:
            return 5   # RETAIN
        elif composite_score >= 30:
            return 3   # CAUTION
        else:
            return 2   # AVOID
    
    def map_priority_to_npl_grade(self, priority: int) -> Tuple[str, str]:
        """
        Map priority to NPL auction grade and bid range.
        
        NPL Structure:
        - Grade A: ₨10-15 Lakhs (Max 3 players)
        - Grade B: ₨5-10 Lakhs (Max 4 players)  
        - Grade C: ₨2-5 Lakhs (Max 3 players)
        
        Args:
            priority: Priority level (0-10)
            
        Returns:
            Tuple of (grade, bid_range)
        """
        if priority >= 9:
            return ('Grade A', '₨13-15 Lakhs')
        elif priority == 8:
            return ('Grade A/B', '₨8-10 Lakhs')
        elif priority == 7:
            return ('Grade B', '₨6-8 Lakhs')
        elif priority == 5:
            return ('Grade B/C', '₨5-7 Lakhs')
        elif priority == 3:
            return ('Grade C', '₨2-5 Lakhs')
        else:
            return ('Skip', 'Below minimum')
    
    def generate_recommendation(self, player_name: str, role: str, 
                               trend: str, s3_pred: float, 
                               metric: str) -> Dict:
        """
        Generate auction/retention recommendation (legacy for batters).
        
        Args:
            player_name: Player name
            role: Player role (batter, bowler, all-rounder)
            trend: Trend classification
            s3_pred: S3 predicted value
            metric: Primary metric
            
        Returns:
            Dictionary with recommendation
        """
        if trend == 'CATASTROPHIC_DECLINE':
            return {
                'decision': '❌ DO NOT RETAIN',
                'priority': 0,
                'max_bid': 0,
                'reason': f'{metric} collapse - high risk of continued decline'
            }
        elif trend == 'DECLINING':
            return {
                'decision': '⚠️ CAUTION',
                'priority': 2,
                'max_bid': '₨5-8 lakh',
                'reason': f'{metric} declining - only if backup option'
            }
        elif trend == 'IMPROVING':
            return {
                'decision': '✅ TARGET',
                'priority': 8,
                'max_bid': '₨15-20 lakh',
                'reason': f'{metric} improving - high potential for S3'
            }
        else:  # STABLE
            return {
                'decision': '🟡 RETAIN/SIGN',
                'priority': 5,
                'max_bid': '₨10-15 lakh',
                'reason': f'{metric} stable - reliable performer'
            }
    
    def forecast_bowlers(self) -> pd.DataFrame:
        """
        Forecast S3 bowling performance for all bowlers.
        
        v2.2 Features:
        - Composite scoring: 60% wickets/match + 30% economy + 10% SR
        - Wickets normalized by playing time (fair comparison)
        - Projection-based confidence intervals (relative to magnitude + volatility)
        - Trend-based predictions (rewards genuine improvers like Sher Malla 7→17 wickets)
        
        Returns:
            DataFrame with S3 predictions and recommendations
        """
        # Merge S1 and S2 data
        bowlers = pd.merge(
            self.s1_data[self.s1_data['role'].str.contains('bowl', case=False, na=False)],
            self.s2_data[self.s2_data['role'].str.contains('bowl', case=False, na=False)],
            on='player_name',
            how='outer',
            suffixes=('_s1', '_s2')
        )
        
        predictions = []
        
        for _, row in bowlers.iterrows():
            player = row['player_name']
            
            # Extract S1 and S2 metrics
            s1_economy = row.get('economy_s1', np.nan)
            s2_economy = row.get('economy_s2', np.nan)
            s1_wickets = row.get('wickets_s1', np.nan)
            s2_wickets = row.get('wickets_s2', np.nan)
            
            # Get bowling matches (estimate if missing)
            s1_bowling_matches = row.get('bowling_matches_s1', 8.0)  # Default 8 matches
            s2_bowling_matches = row.get('bowling_matches_s2', 8.0)
            
            # Calculate wickets per match (normalized)
            s1_wkts_per_match = s1_wickets / s1_bowling_matches if not pd.isna(s1_wickets) else np.nan
            s2_wkts_per_match = s2_wickets / s2_bowling_matches if not pd.isna(s2_wickets) else np.nan
            
            # Get balls bowled to calculate bowling SR
            s1_balls = row.get('balls_bowled_s1', np.nan)
            s2_balls = row.get('balls_bowled_s2', np.nan)
            
            # Calculate bowling strike rate (balls per wicket)
            s1_bowling_sr = s1_balls / s1_wickets if (not pd.isna(s1_balls) and not pd.isna(s1_wickets) and s1_wickets > 0) else np.nan
            s2_bowling_sr = s2_balls / s2_wickets if (not pd.isna(s2_balls) and not pd.isna(s2_wickets) and s2_wickets > 0) else np.nan
            
            # Analyze trends
            economy_trend = self.analyze_trend(s1_economy, s2_economy, 'economy')
            wickets_trend = self.analyze_trend(s1_wickets, s2_wickets, 'wickets')
            wkts_per_match_trend = self.analyze_trend(s1_wkts_per_match, s2_wkts_per_match, 'wickets')
            
            # Predict S3 values using trend-based approach
            s3_economy_pred, s3_economy_lower, s3_economy_upper = self.predict_s3_value(
                s1_economy, s2_economy, economy_trend['trend']
            )
            
            # Predict wickets per match (normalized - v2.0 key feature!)
            s3_wkts_per_match_pred, _, _ = self.predict_s3_value(
                s1_wkts_per_match, s2_wkts_per_match, wkts_per_match_trend['trend']
            )
            
            # Convert back to total wickets (assume 9 matches S3)
            expected_s3_matches = 9
            s3_wickets_pred = s3_wkts_per_match_pred * expected_s3_matches if not pd.isna(s3_wkts_per_match_pred) else np.nan
            
            # v2.2: Projection-based confidence intervals
            # Width scales with prediction magnitude and trend volatility
            if not pd.isna(s3_wickets_pred):
                # Base margin: 25% of predicted value, min 2.0 wickets
                wkt_volatility = abs(s2_wickets - s1_wickets) if not pd.isna(s1_wickets) else 5.0
                wkt_margin = max(2.0, s3_wickets_pred * 0.25, wkt_volatility * 0.5)
                s3_wickets_lower = max(0, s3_wickets_pred - wkt_margin)
                s3_wickets_upper = s3_wickets_pred + wkt_margin
            else:
                s3_wickets_lower = np.nan
                s3_wickets_upper = np.nan
            
            if not pd.isna(s3_economy_pred):
                econ_volatility = abs(s2_economy - s1_economy) if not pd.isna(s1_economy) else 1.0
                econ_margin = max(0.5, s3_economy_pred * 0.12, econ_volatility * 0.4)
                s3_economy_lower = max(0, s3_economy_pred - econ_margin)
                s3_economy_upper = s3_economy_pred + econ_margin
            else:
                s3_economy_lower = np.nan
                s3_economy_upper = np.nan
            
            # Predict bowling SR (tends to be stable)
            s3_bowling_sr_pred, _, _ = self.predict_s3_value(
                s1_bowling_sr, s2_bowling_sr, 'STABLE'  # SR trends tend to be stable
            )
            
            # Calculate composite score (v2.0 key feature!)
            composite_score = self.calculate_composite_bowler_score(
                s2_wkts_per_match,  # Use S2 actual for current value
                s2_economy,
                s2_bowling_sr
            )
            
            # Calculate S3 composite score
            s3_composite_score = self.calculate_composite_bowler_score(
                s3_wkts_per_match_pred,
                s3_economy_pred,
                s3_bowling_sr_pred
            )
            
            # Assign priority based on S3 composite score
            priority = self.assign_priority_from_composite(s3_composite_score)
            
            # Map to NPL grade
            npl_grade, bid_range = self.map_priority_to_npl_grade(priority)
            
            # Generate recommendation description
            if priority >= 9:
                decision = '🔥 ELITE TARGET'
                reason = f'Composite score {s3_composite_score:.1f}/100 - elite wicket-taker'
            elif priority == 8:
                decision = '✅ TARGET'
                reason = f'Composite score {s3_composite_score:.1f}/100 - high-value bowler'
            elif priority == 7:
                decision = '🟢 PRIORITY'
                reason = f'Composite score {s3_composite_score:.1f}/100 - solid performer'
            elif priority == 5:
                decision = '🟡 RETAIN/SIGN'
                reason = f'Composite score {s3_composite_score:.1f}/100 - reliable option'
            elif priority == 3:
                decision = '⚠️ CAUTION'
                reason = f'Composite score {s3_composite_score:.1f}/100 - depth piece only'
            else:
                decision = '❌ AVOID'
                reason = f'Composite score {s3_composite_score:.1f}/100 - high risk'
            
            predictions.append({
                'player_name': player,
                'role': 'Bowler',
                # Economy metrics
                's1_economy': s1_economy,
                's2_economy': s2_economy,
                's3_economy_pred': s3_economy_pred,
                's3_economy_range': f"{s3_economy_lower:.2f}-{s3_economy_upper:.2f}" if s3_economy_pred else None,
                'economy_trend': economy_trend['trend'],
                # Wickets metrics (raw)
                's1_wickets': s1_wickets,
                's2_wickets': s2_wickets,
                's3_wickets_pred': s3_wickets_pred,
                's3_wickets_range': f"{s3_wickets_lower:.1f}-{s3_wickets_upper:.1f}" if s3_wickets_pred else None,
                'wickets_trend': wickets_trend['trend'],
                # Wickets per match (normalized) - v2.0 feature
                's2_wkts_per_match': s2_wkts_per_match,
                's3_wkts_per_match_pred': s3_wkts_per_match_pred,
                # Bowling strike rate
                's2_bowling_sr': s2_bowling_sr,
                's3_bowling_sr_pred': s3_bowling_sr_pred,
                # Composite scoring - v2.0 key feature
                's2_composite_score': composite_score,
                's3_composite_score': s3_composite_score,
                # Priority and NPL mapping
                'priority': priority,
                'npl_grade': npl_grade,
                'bid_range': bid_range,
                # Recommendations
                'recommendation': decision,
                'reason': reason
            })
        
        return pd.DataFrame(predictions).sort_values('priority', ascending=False)
    
    def forecast_batters(self) -> pd.DataFrame:
        """
        Forecast S3 batting performance for all batters.
        
        Returns:
            DataFrame with S3 predictions and recommendations
        """
        # Merge S1 and S2 data
        batters = pd.merge(
            self.s1_data[self.s1_data['role'].str.contains('bat', case=False, na=False)],
            self.s2_data[self.s2_data['role'].str.contains('bat', case=False, na=False)],
            on='player_name',
            how='outer',
            suffixes=('_s1', '_s2')
        )
        
        predictions = []
        
        for _, row in batters.iterrows():
            player = row['player_name']
            
            # Extract S1 and S2 metrics
            s1_runs = row.get('runs_s1', np.nan)
            s2_runs = row.get('runs_s2', np.nan)
            s1_average = row.get('average_s1', np.nan)
            s2_average = row.get('average_s2', np.nan)
            s1_sr = row.get('strike_rate_s1', np.nan)
            s2_sr = row.get('strike_rate_s2', np.nan)
            
            # Analyze trends
            runs_trend = self.analyze_trend(s1_runs, s2_runs, 'runs')
            sr_trend = self.analyze_trend(s1_sr, s2_sr, 'strike_rate')
            
            # Predict S3 values
            s3_runs_pred, s3_runs_lower, s3_runs_upper = self.predict_s3_value(
                s1_runs, s2_runs, runs_trend['trend']
            )
            s3_sr_pred, s3_sr_lower, s3_sr_upper = self.predict_s3_value(
                s1_sr, s2_sr, sr_trend['trend']
            )
            
            # Generate recommendation (based on runs as primary metric)
            recommendation = self.generate_recommendation(
                player, 'batter', runs_trend['trend'], 
                s3_runs_pred, 'Runs'
            )
            
            predictions.append({
                'player_name': player,
                'role': 'Batter',
                's1_runs': s1_runs,
                's2_runs': s2_runs,
                's3_runs_pred': s3_runs_pred,
                's3_runs_range': f"{s3_runs_lower}-{s3_runs_upper}" if s3_runs_pred else None,
                'runs_trend': runs_trend['trend'],
                'runs_delta': runs_trend['delta'],
                's1_strike_rate': s1_sr,
                's2_strike_rate': s2_sr,
                's3_strike_rate_pred': s3_sr_pred,
                's3_sr_range': f"{s3_sr_lower}-{s3_sr_upper}" if s3_sr_pred else None,
                'sr_trend': sr_trend['trend'],
                'recommendation': recommendation['decision'],
                'priority': recommendation['priority'],
                'max_bid': recommendation['max_bid'],
                'reason': recommendation['reason']
            })
        
        return pd.DataFrame(predictions).sort_values('priority', ascending=False)
    
    def generate_full_forecast(self, export_path: str = None) -> Dict[str, pd.DataFrame]:
        """
        Generate complete S3 forecast for all players.
        
        Args:
            export_path: Optional path to save CSV exports
            
        Returns:
            Dictionary with bowler and batter forecasts
        """
        print("\n" + "="*80)
        print("S3 PLAYER PERFORMANCE FORECASTER")
        print("="*80)
        print(f"Analyzing S1 → S2 trends to predict S3 performance...")
        print(f"S1 Players: {len(self.s1_data)}")
        print(f"S2 Players: {len(self.s2_data)}")
        print("="*80 + "\n")
        
        # Generate forecasts
        bowler_forecast = self.forecast_bowlers()
        batter_forecast = self.forecast_batters()
        
        print(f"✓ Bowler Forecast: {len(bowler_forecast)} players analyzed")
        print(f"✓ Batter Forecast: {len(batter_forecast)} players analyzed\n")
        
        # Export if path provided
        if export_path:
            Path(export_path).mkdir(parents=True, exist_ok=True)
            
            bowler_file = Path(export_path) / 's3_bowler_forecast.csv'
            batter_file = Path(export_path) / 's3_batter_forecast.csv'
            
            bowler_forecast.to_csv(bowler_file, index=False)
            batter_forecast.to_csv(batter_file, index=False)
            
            print(f"✓ Exported bowler forecast: {bowler_file}")
            print(f"✓ Exported batter forecast: {batter_file}\n")
        
        # Print summary statistics
        print("="*80)
        print("BOWLER FORECAST SUMMARY")
        print("="*80)
        print(bowler_forecast[['player_name', 's2_economy', 's3_economy_pred', 
                              'economy_trend', 'recommendation']].head(10).to_string(index=False))
        
        print("\n" + "="*80)
        print("BATTER FORECAST SUMMARY")
        print("="*80)
        print(batter_forecast[['player_name', 's2_runs', 's3_runs_pred', 
                              'runs_trend', 'recommendation']].head(10).to_string(index=False))
        
        print("\n" + "="*80)
        print("FORECAST COMPLETE")
        print("="*80 + "\n")
        
        return {
            'bowlers': bowler_forecast,
            'batters': batter_forecast
        }


def main():
    """
    Main execution function.
    Run this after user provides S2 full player data.
    """
    print("\n⏳ Waiting for S2 full player data...")
    print("📋 Expected data structure:")
    print("   - player_name, role, runs, average, strike_rate, wickets, economy")
    print("   - Separate files: s1_player_stats.csv, s2_player_stats.csv")
    print("   - Or combined file with 'season' column\n")
    print("Once data is available, this script will:")
    print("  1. Load S1 and S2 player statistics")
    print("  2. Analyze S1 → S2 trends (improving/declining/stable)")
    print("  3. Predict S3 values with confidence intervals")
    print("  4. Generate auction recommendations (retain/sign/avoid)")
    print("  5. Export forecasts to CSV\n")
    
    # Placeholder - will be activated when data is provided
    # data_dir = Path('data/exports/')
    # s1_data = pd.read_csv(data_dir / 's1_player_stats.csv')
    # s2_data = pd.read_csv(data_dir / 's2_player_stats.csv')
    # 
    # forecaster = S3PerformanceForecaster(s1_data, s2_data)
    # results = forecaster.generate_full_forecast(export_path='data/exports/')
    # 
    # print("✅ S3 forecast complete! Check data/exports/ for results.")


if __name__ == '__main__':
    main()
