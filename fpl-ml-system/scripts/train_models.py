#!/usr/bin/env python3
"""Script to train ML models for player performance prediction."""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add src directory to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from flask import Flask
from src.config import get_config
from src.models.db_models import db
from src.services.prediction_service import PredictionService


def setup_logging(log_level: str = 'INFO'):
    """Set up logging configuration."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('logs/train_models.log')
        ]
    )


def create_app() -> Flask:
    """Create Flask application for model training."""
    app = Flask(__name__)
    
    # Load configuration
    config_name = os.environ.get('FLASK_ENV', 'development')
    config = get_config(config_name)
    app.config.from_object(config)
    
    # Initialize database
    db.init_app(app)
    
    return app


def train_model(prediction_service: PredictionService, 
                test_size: float = 0.2, 
                cv_folds: int = 5,
                lookback_days: int = 90) -> dict:
    """Train the XGBoost model."""
    logger = logging.getLogger(__name__)
    
    logger.info("Starting model training process...")
    start_time = datetime.now()
    
    try:
        # Set lookback period for training data
        if hasattr(prediction_service, 'prepare_training_data'):
            # Temporarily modify method to use custom lookback
            original_method = prediction_service.prepare_training_data
            
            def custom_prepare_training_data():
                return original_method(lookback_days=lookback_days)
            
            prediction_service.prepare_training_data = custom_prepare_training_data
        
        # Train model
        results = prediction_service.train_model(test_size=test_size, cv_folds=cv_folds)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Add timing information
        results['training_duration_seconds'] = duration
        results['training_completed_at'] = end_time.isoformat()
        results['lookback_days'] = lookback_days
        
        logger.info(f"Model training completed successfully in {duration:.2f} seconds")
        logger.info(f"Model version: {results['model_version']}")
        logger.info(f"Test RMSE: {results['test_rmse']:.3f}")
        logger.info(f"Test MAE: {results['test_mae']:.3f}")
        
        return results
        
    except Exception as e:
        logger.error(f"Model training failed: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'training_completed_at': datetime.now().isoformat()
        }


def evaluate_model(prediction_service: PredictionService) -> dict:
    """Evaluate trained model performance."""
    logger = logging.getLogger(__name__)
    
    if not prediction_service.model_loaded:
        logger.error("No model loaded for evaluation")
        return {'success': False, 'error': 'No model loaded'}
    
    logger.info("Evaluating model performance...")
    
    try:
        from src.models.db_models import Player
        
        # Get sample players for evaluation
        sample_players = Player.query.filter(
            Player.status == 'a'
        ).limit(10).all()
        
        if not sample_players:
            return {'success': False, 'error': 'No active players found for evaluation'}
        
        # Make sample predictions
        predictions = []
        for player in sample_players:
            pred = prediction_service.predict_player_points(player.player_id)
            if pred is not None:
                predictions.append({
                    'player_id': player.player_id,
                    'player_name': player.web_name,
                    'position': player.position,
                    'predicted_points': pred,
                    'current_form': float(player.form or 0),
                    'total_points': player.total_points
                })
        
        # Basic evaluation metrics
        if predictions:
            pred_points = [p['predicted_points'] for p in predictions]
            avg_prediction = sum(pred_points) / len(pred_points)
            min_prediction = min(pred_points)
            max_prediction = max(pred_points)
            
            evaluation_results = {
                'success': True,
                'model_version': prediction_service.model_version,
                'evaluation_timestamp': datetime.now().isoformat(),
                'sample_predictions': predictions,
                'summary': {
                    'total_predictions': len(predictions),
                    'avg_predicted_points': round(avg_prediction, 2),
                    'min_predicted_points': round(min_prediction, 2),
                    'max_predicted_points': round(max_prediction, 2)
                }
            }
            
            logger.info(f"Evaluation completed for {len(predictions)} players")
            logger.info(f"Average predicted points: {avg_prediction:.2f}")
            
            return evaluation_results
        else:
            return {'success': False, 'error': 'No valid predictions generated'}
            
    except Exception as e:
        logger.error(f"Model evaluation failed: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}


def update_player_predictions(prediction_service: PredictionService) -> dict:
    """Update predictions for all players in database."""
    logger = logging.getLogger(__name__)
    
    if not prediction_service.model_loaded:
        logger.error("No model loaded for predictions update")
        return {'success': False, 'error': 'No model loaded'}
    
    logger.info("Updating player predictions in database...")
    start_time = datetime.now()
    
    try:
        updated_count = prediction_service.update_predictions_in_db()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"Updated predictions for {updated_count} players in {duration:.2f} seconds")
        
        return {
            'success': True,
            'updated_count': updated_count,
            'duration_seconds': duration,
            'update_completed_at': end_time.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to update player predictions: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}


def save_training_report(results: dict, output_file: str = None):
    """Save training results to JSON file."""
    if output_file is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'logs/training_report_{timestamp}.json'
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Training report saved to: {output_file}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Train ML models for FPL player prediction')
    
    parser.add_argument(
        '--action',
        choices=['train', 'evaluate', 'update-predictions', 'all'],
        default='train',
        help='Action to perform (default: train)'
    )
    
    parser.add_argument(
        '--test-size',
        type=float,
        default=0.2,
        help='Test set size for training (default: 0.2)'
    )
    
    parser.add_argument(
        '--cv-folds',
        type=int,
        default=5,
        help='Number of cross-validation folds (default: 5)'
    )
    
    parser.add_argument(
        '--lookback-days',
        type=int,
        default=90,
        help='Number of days to look back for training data (default: 90)'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )
    
    parser.add_argument(
        '--save-report',
        action='store_true',
        help='Save training report to JSON file'
    )
    
    parser.add_argument(
        '--output-file',
        type=str,
        help='Output file path for training report'
    )
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    logger.info("FPL Model Training Starting...")
    logger.info(f"Arguments: {vars(args)}")
    
    try:
        # Create Flask app
        app = create_app()
        
        with app.app_context():
            # Initialize prediction service
            prediction_service = PredictionService(app)
            
            results = {'actions_completed': [], 'errors': []}
            
            # Perform requested actions
            if args.action in ['train', 'all']:
                logger.info("=" * 50)
                logger.info("TRAINING MODEL")
                logger.info("=" * 50)
                
                training_results = train_model(
                    prediction_service, 
                    args.test_size, 
                    args.cv_folds,
                    args.lookback_days
                )
                
                results['training'] = training_results
                
                if 'error' not in training_results:
                    results['actions_completed'].append('train')
                    logger.info("✅ Model training completed successfully")
                else:
                    results['errors'].append(f"Training failed: {training_results['error']}")
                    logger.error("❌ Model training failed")
            
            if args.action in ['evaluate', 'all']:
                logger.info("=" * 50)
                logger.info("EVALUATING MODEL")
                logger.info("=" * 50)
                
                evaluation_results = evaluate_model(prediction_service)
                results['evaluation'] = evaluation_results
                
                if evaluation_results.get('success', False):
                    results['actions_completed'].append('evaluate')
                    logger.info("✅ Model evaluation completed successfully")
                else:
                    results['errors'].append(f"Evaluation failed: {evaluation_results.get('error', 'Unknown error')}")
                    logger.error("❌ Model evaluation failed")
            
            if args.action in ['update-predictions', 'all']:
                logger.info("=" * 50)
                logger.info("UPDATING PREDICTIONS")
                logger.info("=" * 50)
                
                update_results = update_player_predictions(prediction_service)
                results['predictions_update'] = update_results
                
                if update_results.get('success', False):
                    results['actions_completed'].append('update-predictions')
                    logger.info("✅ Predictions update completed successfully")
                else:
                    results['errors'].append(f"Predictions update failed: {update_results.get('error', 'Unknown error')}")
                    logger.error("❌ Predictions update failed")
            
            # Summary
            logger.info("=" * 50)
            logger.info("SUMMARY")
            logger.info("=" * 50)
            
            if results['actions_completed']:
                logger.info(f"✅ Completed actions: {', '.join(results['actions_completed'])}")
            
            if results['errors']:
                logger.error(f"❌ Errors: {len(results['errors'])}")
                for error in results['errors']:
                    logger.error(f"  - {error}")
            
            # Save report if requested
            if args.save_report:
                save_training_report(results, args.output_file)
            
            # Return appropriate exit code
            return 0 if not results['errors'] else 1
    
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    # Ensure logs directory exists
    os.makedirs('logs', exist_ok=True)
    
    sys.exit(main())