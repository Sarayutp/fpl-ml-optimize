#!/usr/bin/env python3
"""System validation script for FPL AI Optimizer."""

import os
import sys
from pathlib import Path

# Add src directory to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from flask import Flask
from src.config import get_config
from src.models.db_models import db, Team, Player


def create_app() -> Flask:
    """Create Flask application for validation."""
    app = Flask(__name__)
    
    # Load configuration
    config_name = os.environ.get('FLASK_ENV', 'development')
    config = get_config(config_name)
    app.config.from_object(config)
    
    # Initialize database
    db.init_app(app)
    
    return app


def validate_database_schema(app: Flask) -> bool:
    """Validate database schema and structure."""
    print("Validating database schema...")
    
    with app.app_context():
        try:
            # Check database connection
            with db.engine.connect() as conn:
                conn.execute(db.text('SELECT 1'))
            print("✓ Database connection successful")
        except Exception as e:
            print(f"✗ Database connection failed: {e}")
            return False
        
        # Check if all required tables exist
        inspector = db.inspect(db.engine)
        expected_tables = [
            'teams', 'players', 'fixtures', 'player_past_stats',
            'player_predictions', 'users', 'user_teams'
        ]
        
        existing_tables = inspector.get_table_names()
        all_tables_exist = True
        
        for table in expected_tables:
            if table in existing_tables:
                print(f"✓ Table '{table}' exists")
            else:
                print(f"✗ Table '{table}' missing")
                all_tables_exist = False
        
        if not all_tables_exist:
            print("Run 'python scripts/setup_database.py' to create missing tables.")
            return False
        
        # Verify critical indexes
        players_indexes = inspector.get_indexes('players')
        index_names = [idx['name'] for idx in players_indexes]
        
        critical_indexes = ['idx_player_web_name', 'idx_player_team', 'idx_player_position']
        indexes_valid = True
        
        for index_name in critical_indexes:
            if index_name in index_names:
                print(f"✓ Index '{index_name}' exists")
            else:
                print(f"✗ Index '{index_name}' missing")
                indexes_valid = False
        
        if not indexes_valid:
            print("Some critical indexes are missing. Performance may be affected.")
            return False
        
        # Test foreign key constraints
        try:
            # This should work
            team = Team(team_id=999, name='Test Team', short_name='TST')
            db.session.add(team)
            db.session.flush()
            
            player = Player(
                player_id=9999,
                web_name='Test Player',
                team_id=999,
                position='FWD',
                now_cost=50
            )
            db.session.add(player)
            db.session.flush()
            
            # Clean up test data
            db.session.delete(player)
            db.session.delete(team)
            db.session.commit()
            
            print("✓ Foreign key constraints working")
            
        except Exception as e:
            db.session.rollback()
            print(f"✗ Foreign key constraint test failed: {e}")
            return False
        
    return True


def validate_models_import() -> bool:
    """Validate that all models can be imported successfully."""
    print("\nValidating model imports...")
    
    try:
        from src.models.db_models import Team, Player, Fixture, PlayerPastStats, PlayerPrediction, User, UserTeam
        print("✓ Database models imported successfully")
    except Exception as e:
        print(f"✗ Database models import failed: {e}")
        return False
    
    try:
        from src.models.data_models import PlayerStats, OptimizedTeam, TransferSuggestion
        print("✓ Pydantic models imported successfully")
    except Exception as e:
        print(f"✗ Pydantic models import failed: {e}")
        return False
    
    return True


def validate_configuration() -> bool:
    """Validate application configuration."""
    print("\nValidating configuration...")
    
    try:
        from src.config import get_config
        
        config = get_config('development')
        print("✓ Development configuration loaded")
        
        config = get_config('testing')
        print("✓ Testing configuration loaded")
        
        # Check required config values
        dev_config = get_config('development')
        required_attrs = ['SECRET_KEY', 'SQLALCHEMY_DATABASE_URI', 'FPL_API_BASE_URL']
        
        for attr in required_attrs:
            if hasattr(dev_config, attr) and getattr(dev_config, attr):
                print(f"✓ Configuration '{attr}' is set")
            else:
                print(f"✗ Configuration '{attr}' is missing")
                return False
        
    except Exception as e:
        print(f"✗ Configuration validation failed: {e}")
        return False
    
    return True


def validate_directory_structure() -> bool:
    """Validate project directory structure."""
    print("\nValidating directory structure...")
    
    project_root = Path(__file__).parent.parent
    
    required_dirs = [
        'src',
        'src/models',
        'src/services',
        'src/views',
        'src/templates',
        'src/static',
        'tests',
        'scripts',
        'logs',
        'models'
    ]
    
    all_dirs_exist = True
    
    for dir_path in required_dirs:
        full_path = project_root / dir_path
        if full_path.exists():
            print(f"✓ Directory '{dir_path}' exists")
        else:
            print(f"✗ Directory '{dir_path}' missing")
            all_dirs_exist = False
    
    # Check for required files
    required_files = [
        'requirements.txt',
        '.env.example',
        '.gitignore',
        'src/config.py',
        'src/models/db_models.py',
        'src/models/data_models.py'
    ]
    
    all_files_exist = True
    
    for file_path in required_files:
        full_path = project_root / file_path
        if full_path.exists():
            print(f"✓ File '{file_path}' exists")
        else:
            print(f"✗ File '{file_path}' missing")
            all_files_exist = False
    
    return all_dirs_exist and all_files_exist


def main():
    """Main validation function."""
    print("FPL AI Optimizer System Validation")
    print("=" * 50)
    
    validation_results = []
    
    # Run all validations
    validation_results.append(("Directory Structure", validate_directory_structure()))
    validation_results.append(("Model Imports", validate_models_import()))
    validation_results.append(("Configuration", validate_configuration()))
    
    # Database validation requires Flask app
    try:
        app = create_app()
        validation_results.append(("Database Schema", validate_database_schema(app)))
    except Exception as e:
        print(f"✗ Could not create Flask app for database validation: {e}")
        validation_results.append(("Database Schema", False))
    
    # Summary
    print("\n" + "=" * 50)
    print("VALIDATION SUMMARY")
    print("=" * 50)
    
    all_passed = True
    for name, passed in validation_results:
        status = "PASS" if passed else "FAIL"
        print(f"{name:<20}: {status}")
        if not passed:
            all_passed = False
    
    print("=" * 50)
    if all_passed:
        print("🎉 All validations PASSED! System is ready.")
        return 0
    else:
        print("❌ Some validations FAILED. Please fix issues before proceeding.")
        return 1


if __name__ == '__main__':
    sys.exit(main())