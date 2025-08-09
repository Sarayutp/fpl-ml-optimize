"""Prediction service using XGBoost for player performance prediction."""

import logging
import os
import pickle
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

try:
    import numpy as np
    import pandas as pd
    import xgboost as xgb
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    from sklearn.model_selection import train_test_split, cross_val_score
    from sklearn.metrics import mean_squared_error, mean_absolute_error
    ML_AVAILABLE = True
except ImportError as e:
    print(f"Warning: ML libraries not available: {e}")
    ML_AVAILABLE = False
    # Create dummy classes for type hints
    class DummyModule:
        def __init__(self): pass
        def __getattr__(self, name): return DummyModule
        def __call__(self, *args, **kwargs): return DummyModule()
    
    np = DummyModule()
    pd = DummyModule()
    xgb = DummyModule()
    StandardScaler = DummyModule
    LabelEncoder = DummyModule
    train_test_split = DummyModule()
    cross_val_score = DummyModule()
    mean_squared_error = DummyModule()
    mean_absolute_error = DummyModule()

from flask import current_app

from ..models.db_models import db, Player, Team, Fixture, PlayerPastStats, PlayerPrediction


logger = logging.getLogger(__name__)


class PredictionService:
    """Service for ML-based player performance prediction."""
    
    def __init__(self, app=None):
        """Initialize prediction service."""
        self.app = app
        self.model = None
        self.scaler = None
        self.label_encoders = {}
        self.feature_columns = []
        self.model_version = None
        self.model_loaded = False
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the prediction service with Flask app."""
        self.app = app
        self.model_path = app.config.get('XGBOOST_MODEL_PATH', 'models/xgboost_player_predictions.json')
        
        # Try to load existing model
        self.load_model()
    
    def load_model(self) -> bool:
        """Load trained model and preprocessing objects."""
        if not ML_AVAILABLE:
            logger.warning("ML libraries not available, using fallback predictions")
            return False
            
        try:
            model_dir = os.path.dirname(self.model_path)
            
            # Load XGBoost model
            if os.path.exists(self.model_path):
                self.model = xgb.Booster()
                self.model.load_model(self.model_path)
                logger.info(f"Loaded XGBoost model from {self.model_path}")
            else:
                logger.warning(f"Model file not found: {self.model_path}")
                return False
            
            # Load scaler
            scaler_path = os.path.join(model_dir, 'scaler.pkl')
            if os.path.exists(scaler_path):
                with open(scaler_path, 'rb') as f:
                    self.scaler = pickle.load(f)
                logger.info("Loaded feature scaler")
            
            # Load label encoders
            encoders_path = os.path.join(model_dir, 'label_encoders.pkl')
            if os.path.exists(encoders_path):
                with open(encoders_path, 'rb') as f:
                    self.label_encoders = pickle.load(f)
                logger.info("Loaded label encoders")
            
            # Load feature columns
            features_path = os.path.join(model_dir, 'feature_columns.pkl')
            if os.path.exists(features_path):
                with open(features_path, 'rb') as f:
                    self.feature_columns = pickle.load(f)
                logger.info(f"Loaded {len(self.feature_columns)} feature columns")
            
            # Load model metadata
            metadata_path = os.path.join(model_dir, 'model_metadata.pkl')
            if os.path.exists(metadata_path):
                with open(metadata_path, 'rb') as f:
                    metadata = pickle.load(f)
                    self.model_version = metadata.get('version', 'unknown')
                logger.info(f"Model version: {self.model_version}")
            
            self.model_loaded = True
            return True
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            self.model_loaded = False
            return False
    
    def save_model(self, model: xgb.Booster, scaler: StandardScaler, 
                   label_encoders: Dict, feature_columns: List[str],
                   model_version: str = None) -> bool:
        """Save trained model and preprocessing objects."""
        try:
            model_dir = os.path.dirname(self.model_path)
            os.makedirs(model_dir, exist_ok=True)
            
            # Save XGBoost model
            model.save_model(self.model_path)
            logger.info(f"Saved XGBoost model to {self.model_path}")
            
            # Save scaler
            scaler_path = os.path.join(model_dir, 'scaler.pkl')
            with open(scaler_path, 'wb') as f:
                pickle.dump(scaler, f)
            
            # Save label encoders
            encoders_path = os.path.join(model_dir, 'label_encoders.pkl')
            with open(encoders_path, 'wb') as f:
                pickle.dump(label_encoders, f)
            
            # Save feature columns
            features_path = os.path.join(model_dir, 'feature_columns.pkl')
            with open(features_path, 'wb') as f:
                pickle.dump(feature_columns, f)
            
            # Save model metadata
            metadata = {
                'version': model_version or datetime.now().strftime('%Y%m%d_%H%M%S'),
                'created_at': datetime.now().isoformat(),
                'feature_count': len(feature_columns),
                'framework': 'xgboost'
            }
            metadata_path = os.path.join(model_dir, 'model_metadata.pkl')
            with open(metadata_path, 'wb') as f:
                pickle.dump(metadata, f)
            
            # Update instance variables
            self.model = model
            self.scaler = scaler
            self.label_encoders = label_encoders
            self.feature_columns = feature_columns
            self.model_version = metadata['version']
            self.model_loaded = True
            
            logger.info("Model and preprocessing objects saved successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error saving model: {e}")
            return False
    
    def prepare_training_data(self, lookback_days: int = 90) -> Tuple[pd.DataFrame, pd.Series]:
        """Prepare training data from database."""
        logger.info(f"Preparing training data with {lookback_days} days lookback...")
        
        # Try to get historical data first
        cutoff_date = datetime.now() - timedelta(days=lookback_days)
        
        # Check if we have historical data
        historical_count = PlayerPastStats.query.filter(
            PlayerPastStats.created_at >= cutoff_date
        ).count()
        
        if historical_count == 0:
            logger.warning("No historical PlayerPastStats found. Using synthetic training data.")
            return self._create_synthetic_training_data()
        
        # Use historical data if available
        return self._prepare_historical_training_data(cutoff_date)
    
    def _prepare_historical_training_data(self, cutoff_date: datetime) -> Tuple[pd.DataFrame, pd.Series]:
        """Prepare training data from historical stats."""
        # Query for training data
        query = db.session.query(
            PlayerPastStats.player_id,
            PlayerPastStats.total_points,
            PlayerPastStats.minutes,
            PlayerPastStats.goals_scored,
            PlayerPastStats.assists,
            PlayerPastStats.clean_sheets,
            PlayerPastStats.was_home,
            Player.position,
            Player.now_cost,
            Player.form,
            Player.expected_goals,
            Player.expected_assists,
            Team.strength_overall_home,
            Team.strength_overall_away,
            Fixture.home_difficulty,
            Fixture.away_difficulty,
            Fixture.gameweek
        ).join(
            Player, PlayerPastStats.player_id == Player.player_id
        ).join(
            Team, Player.team_id == Team.team_id
        ).join(
            Fixture, PlayerPastStats.fixture_id == Fixture.fixture_id
        ).filter(
            PlayerPastStats.created_at >= cutoff_date
        )
        
        # Convert to DataFrame
        df = pd.read_sql(query.statement, db.engine)
        
        logger.info(f"Retrieved {len(df)} historical training samples")
        
        # Feature engineering
        features_df = self._engineer_features(df)
        
        # Target variable (total_points)
        target = df['total_points'].values
        
        return features_df, target
    
    def _create_synthetic_training_data(self) -> Tuple[pd.DataFrame, pd.Series]:
        """Create synthetic training data based on current player stats."""
        logger.info("Creating synthetic training data from current player stats...")
        
        # Get all players with their teams
        players_query = db.session.query(
            Player.player_id,
            Player.position,
            Player.now_cost,
            Player.form,
            Player.expected_goals,
            Player.expected_assists,
            Player.total_points,
            Player.points_per_game,
            Player.minutes,
            Team.strength_overall_home,
            Team.strength_overall_away
        ).join(Team, Player.team_id == Team.team_id).filter(
            Player.status == 'a',
            Player.total_points > 0  # Only players with some points
        )
        
        df = pd.read_sql(players_query.statement, db.engine)
        
        if df.empty:
            raise ValueError("No player data found for training. Please fetch FPL data first.")
        
        logger.info(f"Using {len(df)} current players for synthetic training data")
        
        # Create synthetic match scenarios for each player
        synthetic_data = []
        np.random.seed(42)  # For reproducible results
        
        for _, player in df.iterrows():
            # Generate multiple scenarios per player (5-10 matches)
            num_matches = np.random.randint(5, 11)
            
            for match in range(num_matches):
                # Random fixture scenarios
                was_home = np.random.choice([True, False])
                fixture_difficulty = np.random.randint(1, 6)  # 1-5 difficulty
                gameweek = np.random.randint(1, 38)
                
                # Estimate points based on current stats + randomness
                base_ppg = float(player['points_per_game'] or 0)
                form_factor = float(player['form'] or 0) / 10.0
                
                # Adjust for fixture difficulty (easier = more points)
                difficulty_multiplier = (6 - fixture_difficulty) / 5.0  # 0.2 to 1.0
                
                # Home advantage
                home_bonus = 0.5 if was_home else 0
                
                # Generate synthetic points with some variance
                expected_points = max(0, base_ppg * difficulty_multiplier + form_factor + home_bonus)
                actual_points = max(0, np.random.normal(expected_points, expected_points * 0.3))
                
                synthetic_row = {
                    'player_id': player['player_id'],
                    'total_points': actual_points,
                    'minutes': min(90, max(0, int(np.random.normal(60, 20)))),
                    'goals_scored': max(0, int(np.random.poisson(float(player['expected_goals'] or 0) * 0.1))),
                    'assists': max(0, int(np.random.poisson(float(player['expected_assists'] or 0) * 0.1))),
                    'clean_sheets': 1 if (player['position'] in ['GKP', 'DEF'] and np.random.random() < 0.3) else 0,
                    'was_home': was_home,
                    'position': player['position'],
                    'now_cost': player['now_cost'],
                    'form': player['form'],
                    'expected_goals': player['expected_goals'],
                    'expected_assists': player['expected_assists'],
                    'strength_overall_home': player['strength_overall_home'],
                    'strength_overall_away': player['strength_overall_away'],
                    'home_difficulty': fixture_difficulty if was_home else np.random.randint(1, 6),
                    'away_difficulty': fixture_difficulty if not was_home else np.random.randint(1, 6),
                    'gameweek': gameweek
                }
                
                synthetic_data.append(synthetic_row)
        
        synthetic_df = pd.DataFrame(synthetic_data)
        logger.info(f"Created {len(synthetic_df)} synthetic training samples")
        
        # Feature engineering
        features_df = self._engineer_features(synthetic_df)
        
        # Target variable (total_points)
        target = synthetic_df['total_points'].values
        
        return features_df, target
    
    def _engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Engineer features for ML model."""
        features = df.copy()
        
        # Basic features
        features['cost_millions'] = features['now_cost'] / 10.0
        features['form_numeric'] = pd.to_numeric(features['form'], errors='coerce').fillna(0)
        features['expected_goals_numeric'] = pd.to_numeric(features['expected_goals'], errors='coerce').fillna(0)
        features['expected_assists_numeric'] = pd.to_numeric(features['expected_assists'], errors='coerce').fillna(0)
        
        # Team strength features
        features['team_strength'] = np.where(
            features['was_home'],
            features['strength_overall_home'],
            features['strength_overall_away']
        )
        
        # Fixture difficulty
        features['fixture_difficulty'] = np.where(
            features['was_home'],
            features['home_difficulty'],
            features['away_difficulty']
        )
        
        # Opponent strength (inverse of fixture difficulty)
        features['opponent_weakness'] = 6 - features['fixture_difficulty']  # Invert scale (5=weak, 1=strong)
        
        # Position-based features
        features['is_goalkeeper'] = (features['position'] == 'GKP').astype(int)
        features['is_defender'] = (features['position'] == 'DEF').astype(int)
        features['is_midfielder'] = (features['position'] == 'MID').astype(int)
        features['is_forward'] = (features['position'] == 'FWD').astype(int)
        
        # Value features
        features['value_score'] = features['form_numeric'] / np.maximum(features['cost_millions'], 1.0)
        
        # Expected involvement
        features['expected_goal_involvement'] = (
            features['expected_goals_numeric'] + features['expected_assists_numeric']
        )
        
        # Minutes played indicator
        features['likely_to_play'] = (features['minutes'] > 0).astype(int)
        
        # Home/away
        features['is_home'] = features['was_home'].astype(int)
        
        # Select final feature columns
        feature_cols = [
            'cost_millions', 'form_numeric', 'expected_goals_numeric', 'expected_assists_numeric',
            'team_strength', 'fixture_difficulty', 'opponent_weakness',
            'is_goalkeeper', 'is_defender', 'is_midfielder', 'is_forward',
            'value_score', 'expected_goal_involvement', 'likely_to_play', 'is_home',
            'gameweek'
        ]
        
        # Handle missing values
        for col in feature_cols:
            if col in features.columns:
                features[col] = features[col].fillna(0)
        
        return features[feature_cols]
    
    def train_model(self, test_size: float = 0.2, cv_folds: int = 5) -> Dict[str, Any]:
        """Train XGBoost model with cross-validation."""
        logger.info("Starting model training...")
        
        # Prepare data
        X, y = self.prepare_training_data()
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=None
        )
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Store feature columns
        feature_columns = X.columns.tolist()
        
        # Convert to DMatrix for XGBoost
        dtrain = xgb.DMatrix(X_train_scaled, label=y_train)
        dtest = xgb.DMatrix(X_test_scaled, label=y_test)
        
        # XGBoost parameters optimized for FPL points prediction
        params = {
            'objective': 'reg:squarederror',
            'eval_metric': 'rmse',
            'max_depth': 6,
            'learning_rate': 0.1,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'min_child_weight': 1,
            'reg_alpha': 0.1,
            'reg_lambda': 0.1,
            'random_state': 42,
            'verbosity': 0
        }
        
        # Train model with early stopping
        evals = [(dtrain, 'train'), (dtest, 'test')]
        model = xgb.train(
            params,
            dtrain,
            num_boost_round=1000,
            evals=evals,
            early_stopping_rounds=50,
            verbose_eval=False
        )
        
        # Predictions
        train_pred = model.predict(dtrain)
        test_pred = model.predict(dtest)
        
        # Metrics
        train_rmse = np.sqrt(mean_squared_error(y_train, train_pred))
        test_rmse = np.sqrt(mean_squared_error(y_test, test_pred))
        train_mae = mean_absolute_error(y_train, train_pred)
        test_mae = mean_absolute_error(y_test, test_pred)
        
        # Cross-validation
        cv_scores = cross_val_score(
            xgb.XGBRegressor(**params),
            X_train_scaled, y_train,
            cv=cv_folds,
            scoring='neg_mean_squared_error'
        )
        cv_rmse = np.sqrt(-cv_scores.mean())
        
        # Model version
        model_version = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save model
        label_encoders = {}  # No categorical features to encode in this version
        self.save_model(model, scaler, label_encoders, feature_columns, model_version)
        
        # Training summary
        results = {
            'model_version': model_version,
            'train_samples': len(X_train),
            'test_samples': len(X_test),
            'features': len(feature_columns),
            'train_rmse': train_rmse,
            'test_rmse': test_rmse,
            'train_mae': train_mae,
            'test_mae': test_mae,
            'cv_rmse_mean': cv_rmse,
            'cv_rmse_std': cv_scores.std(),
            'best_iteration': model.best_iteration,
            'feature_importance': dict(zip(feature_columns, model.get_score().values()))
        }
        
        logger.info(f"Model training completed. Test RMSE: {test_rmse:.3f}, Test MAE: {test_mae:.3f}")
        return results
    
    def predict_player_points(self, player_id: int, fixture_id: Optional[int] = None,
                            is_home: Optional[bool] = None) -> Optional[float]:
        """Predict expected points for a specific player."""
        if not ML_AVAILABLE:
            # Fallback prediction based on position and form
            player = Player.query.filter_by(player_id=player_id).first()
            if not player:
                return None
            base_points = {'GKP': 2.0, 'DEF': 2.5, 'MID': 3.0, 'FWD': 3.5}
            form_factor = float(player.form or 0) / 10.0
            cost_factor = (player.now_cost / 10.0) / 5.0
            return max(0.5, base_points.get(player.position, 2.0) * (1 + form_factor + cost_factor * 0.3))
            
        if not self.model_loaded:
            logger.warning("Model not loaded. Cannot make predictions.")
            return None
        
        try:
            # Get player data
            player = Player.query.filter_by(player_id=player_id).first()
            if not player:
                logger.warning(f"Player {player_id} not found")
                return None
            
            # Get fixture data if provided
            fixture_difficulty = 3  # Default neutral difficulty
            gameweek = 1  # Default gameweek
            
            if fixture_id:
                fixture = Fixture.query.filter_by(fixture_id=fixture_id).first()
                if fixture:
                    if is_home is None:
                        is_home = (fixture.home_team_id == player.team_id)
                    
                    fixture_difficulty = (fixture.home_difficulty if is_home 
                                        else fixture.away_difficulty) or 3
                    gameweek = fixture.gameweek or 1
            
            # Prepare feature vector
            features = self._prepare_prediction_features(player, fixture_difficulty, is_home or False, gameweek)
            
            if features is None:
                return None
            
            # Make prediction
            features_scaled = self.scaler.transform([features])
            dmatrix = xgb.DMatrix(features_scaled)
            prediction = self.model.predict(dmatrix)[0]
            
            # Ensure non-negative prediction
            prediction = max(0.0, prediction)
            
            return round(prediction, 2)
            
        except Exception as e:
            logger.error(f"Error predicting points for player {player_id}: {e}")
            return None
    
    def _prepare_prediction_features(self, player: Player, fixture_difficulty: int,
                                   is_home: bool, gameweek: int) -> Optional[List[float]]:
        """Prepare feature vector for a single prediction."""
        try:
            # Basic player features
            cost_millions = player.now_cost / 10.0
            form_numeric = float(player.form or 0)
            expected_goals_numeric = float(player.expected_goals or 0)
            expected_assists_numeric = float(player.expected_assists or 0)
            
            # Team strength
            team_strength = (player.team.strength_overall_home if is_home 
                           else player.team.strength_overall_away) if player.team else 3
            
            # Opponent weakness
            opponent_weakness = 6 - fixture_difficulty
            
            # Position indicators
            is_goalkeeper = 1 if player.position == 'GKP' else 0
            is_defender = 1 if player.position == 'DEF' else 0
            is_midfielder = 1 if player.position == 'MID' else 0
            is_forward = 1 if player.position == 'FWD' else 0
            
            # Value score
            value_score = form_numeric / max(cost_millions, 1.0)
            
            # Expected involvement
            expected_goal_involvement = expected_goals_numeric + expected_assists_numeric
            
            # Playing likelihood (simplified)
            likely_to_play = 1 if player.status == 'a' else 0
            
            # Home/away
            is_home_int = 1 if is_home else 0
            
            # Build feature vector in same order as training
            features = [
                cost_millions, form_numeric, expected_goals_numeric, expected_assists_numeric,
                team_strength, fixture_difficulty, opponent_weakness,
                is_goalkeeper, is_defender, is_midfielder, is_forward,
                value_score, expected_goal_involvement, likely_to_play, is_home_int,
                gameweek
            ]
            
            return features
            
        except Exception as e:
            logger.error(f"Error preparing features for player {player.player_id}: {e}")
            return None
    
    def predict_multiple_players(self, player_ids: List[int], 
                               fixture_context: Optional[Dict] = None) -> Dict[int, float]:
        """Predict expected points for multiple players."""
        predictions = {}
        
        for player_id in player_ids:
            is_home = None
            fixture_id = None
            
            if fixture_context and player_id in fixture_context:
                context = fixture_context[player_id]
                is_home = context.get('is_home')
                fixture_id = context.get('fixture_id')
            
            prediction = self.predict_player_points(player_id, fixture_id, is_home)
            if prediction is not None:
                predictions[player_id] = prediction
        
        return predictions
    
    def update_predictions_in_db(self, gameweek: Optional[int] = None) -> int:
        """Update predictions in database for all active players."""
        if not self.model_loaded:
            logger.warning("Model not loaded. Cannot update predictions.")
            return 0
        
        logger.info("Updating player predictions in database...")
        
        # Get all active players
        players = Player.query.filter(Player.status == 'a').all()
        
        updated_count = 0
        
        for player in players:
            try:
                # Predict with neutral fixture (difficulty=3, home=True as default)
                expected_points = self.predict_player_points(player.player_id, is_home=True)
                
                if expected_points is not None:
                    # Check if prediction already exists
                    prediction = PlayerPrediction.query.filter_by(
                        player_id=player.player_id,
                        fixture_id=None  # General prediction
                    ).first()
                    
                    if prediction:
                        prediction.expected_points = expected_points
                        prediction.model_version = self.model_version
                        prediction.last_updated = datetime.utcnow()
                    else:
                        prediction = PlayerPrediction(
                            player_id=player.player_id,
                            expected_points=expected_points,
                            model_version=self.model_version
                        )
                        db.session.add(prediction)
                    
                    updated_count += 1
                    
            except Exception as e:
                logger.error(f"Error updating prediction for player {player.player_id}: {e}")
                continue
        
        try:
            db.session.commit()
            logger.info(f"Updated predictions for {updated_count} players")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error committing predictions to database: {e}")
            return 0
        
        return updated_count