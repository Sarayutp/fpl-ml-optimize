#!/usr/bin/env python3
"""Script to fetch and update FPL data from the official API."""

import argparse
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
from src.services.data_service import DataService, FPLAPIError

# Use SimpleCache instead of flask_caching
class SimpleCache:
    """Simple cache implementation."""
    def __init__(self, app=None):
        self.cache_data = {}
        self.app = app
    
    def get(self, key):
        return self.cache_data.get(key)
    
    def set(self, key, value, timeout=300):
        self.cache_data[key] = value
    
    def delete(self, key):
        self.cache_data.pop(key, None)
    
    def clear(self):
        self.cache_data.clear()


def setup_logging(log_level: str = 'INFO'):
    """Set up logging configuration."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('logs/fetch_fpl_data.log')
        ]
    )


def create_app() -> Flask:
    """Create Flask application for data fetching."""
    app = Flask(__name__)
    
    # Load configuration
    config_name = os.environ.get('FLASK_ENV', 'development')
    config = get_config(config_name)
    app.config.from_object(config)
    
    # Initialize extensions
    db.init_app(app)
    cache = SimpleCache(app)
    
    return app, cache


def fetch_all_data(data_service: DataService, force_refresh: bool = False) -> dict:
    """Fetch all data from FPL API and update database."""
    logger = logging.getLogger(__name__)
    
    if force_refresh and data_service.cache:
        logger.info("Force refresh requested - clearing cache...")
        data_service.cache.clear()
    
    logger.info("Starting FPL data fetch...")
    start_time = datetime.now()
    
    try:
        # Update database with latest data
        stats = data_service.update_database_from_api()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"Data fetch completed in {duration:.2f} seconds")
        logger.info(f"Updated: {stats['teams_updated']} teams, {stats['players_updated']} players, "
                   f"{stats['fixtures_updated']} fixtures")
        
        return {
            'success': True,
            'duration_seconds': duration,
            'stats': stats,
            'timestamp': end_time.isoformat()
        }
        
    except FPLAPIError as e:
        logger.error(f"FPL API error: {e}")
        return {
            'success': False,
            'error': f"FPL API error: {e}",
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Unexpected error during data fetch: {e}", exc_info=True)
        return {
            'success': False,
            'error': f"Unexpected error: {e}",
            'timestamp': datetime.now().isoformat()
        }


def fetch_specific_data(data_service: DataService, data_type: str) -> dict:
    """Fetch specific type of data."""
    logger = logging.getLogger(__name__)
    
    logger.info(f"Fetching {data_type} data...")
    start_time = datetime.now()
    
    try:
        if data_type == 'players':
            player_data = data_service.get_player_data()
            stats = data_service._update_players(player_data)
            db.session.commit()
            result_stats = {'players_updated': stats}
            
        elif data_type == 'teams':
            team_data = data_service.get_team_data()
            stats = data_service._update_teams(team_data)
            db.session.commit()
            result_stats = {'teams_updated': stats}
            
        elif data_type == 'fixtures':
            fixture_data = data_service.get_fixture_data()
            stats = data_service._update_fixtures(fixture_data)
            db.session.commit()
            result_stats = {'fixtures_updated': stats}
            
        else:
            raise ValueError(f"Unknown data type: {data_type}")
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"{data_type} fetch completed in {duration:.2f} seconds")
        logger.info(f"Stats: {result_stats}")
        
        return {
            'success': True,
            'duration_seconds': duration,
            'stats': result_stats,
            'timestamp': end_time.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error fetching {data_type}: {e}", exc_info=True)
        db.session.rollback()
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


def test_api_connection(data_service: DataService) -> dict:
    """Test FPL API connection."""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Testing FPL API connection...")
        bootstrap_data = data_service.get_bootstrap_static()
        
        # Basic validation
        required_keys = ['elements', 'teams', 'events']
        for key in required_keys:
            if key not in bootstrap_data:
                raise ValueError(f"Missing required key '{key}' in API response")
        
        players_count = len(bootstrap_data.get('elements', []))
        teams_count = len(bootstrap_data.get('teams', []))
        events_count = len(bootstrap_data.get('events', []))
        
        logger.info(f"API connection successful! Found {players_count} players, "
                   f"{teams_count} teams, {events_count} gameweeks")
        
        return {
            'success': True,
            'players_count': players_count,
            'teams_count': teams_count,
            'events_count': events_count,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"API connection test failed: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Fetch FPL data from official API')
    
    parser.add_argument(
        '--data-type',
        choices=['all', 'players', 'teams', 'fixtures'],
        default='all',
        help='Type of data to fetch (default: all)'
    )
    
    parser.add_argument(
        '--force-refresh',
        action='store_true',
        help='Force refresh by clearing cache'
    )
    
    parser.add_argument(
        '--test-connection',
        action='store_true',
        help='Test API connection without updating database'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be fetched without actually updating database'
    )
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    logger.info("FPL Data Fetcher Starting...")
    logger.info(f"Arguments: {vars(args)}")
    
    try:
        # Create Flask app and data service
        app, cache = create_app()
        
        with app.app_context():
            data_service = DataService(app, cache)
            
            # Test connection if requested
            if args.test_connection:
                result = test_api_connection(data_service)
                if result['success']:
                    logger.info("✅ API connection test passed")
                    return 0
                else:
                    logger.error("❌ API connection test failed")
                    return 1
            
            # Dry run mode
            if args.dry_run:
                logger.info("🔍 DRY RUN MODE - No database changes will be made")
                test_result = test_api_connection(data_service)
                if test_result['success']:
                    logger.info(f"Would fetch data for {test_result['players_count']} players, "
                              f"{test_result['teams_count']} teams")
                return 0
            
            # Fetch data
            if args.data_type == 'all':
                result = fetch_all_data(data_service, args.force_refresh)
            else:
                result = fetch_specific_data(data_service, args.data_type)
            
            # Report results
            if result['success']:
                logger.info("✅ Data fetch completed successfully")
                if 'stats' in result:
                    for key, value in result['stats'].items():
                        logger.info(f"  {key}: {value}")
                return 0
            else:
                logger.error("❌ Data fetch failed")
                logger.error(f"Error: {result.get('error', 'Unknown error')}")
                return 1
    
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