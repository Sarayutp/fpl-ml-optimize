#!/usr/bin/env python3
"""Database setup script for FPL AI Optimizer."""

import os
import sys
from pathlib import Path

# Add src directory to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from flask import Flask
from src.config import get_config
from src.models.db_models import db


def create_app() -> Flask:
    """Create Flask application for database setup."""
    app = Flask(__name__)
    
    # Load configuration
    config_name = os.environ.get('FLASK_ENV', 'development')
    config = get_config(config_name)
    app.config.from_object(config)
    
    # Initialize database
    db.init_app(app)
    
    return app


def setup_database(app: Flask) -> None:
    """Set up database tables and indexes."""
    with app.app_context():
        print("Creating database tables...")
        
        # Drop all tables if they exist (be careful with this in production!)
        if os.environ.get('DROP_EXISTING_TABLES', '').lower() == 'true':
            print("WARNING: Dropping existing tables!")
            db.drop_all()
        
        # Create all tables
        db.create_all()
        
        # Enable foreign key constraints for SQLite
        if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']:
            print("Enabling foreign key constraints for SQLite...")
            with db.engine.connect() as conn:
                conn.execute(db.text('PRAGMA foreign_keys = ON;'))
        
        print("Database setup completed successfully!")
        
        # Print table information
        print("\nCreated tables:")
        inspector = db.inspect(db.engine)
        for table_name in inspector.get_table_names():
            print(f"  - {table_name}")
        
        # Verify indexes
        print("\nVerifying indexes:")
        players_indexes = inspector.get_indexes('players')
        for index in players_indexes:
            print(f"  - players.{index['name']}: {index['column_names']}")


def seed_initial_data(app: Flask) -> None:
    """Seed database with initial data if needed."""
    with app.app_context():
        from src.models.db_models import Team, Player
        
        # Check if teams already exist
        if Team.query.first():
            print("Database already contains data, skipping seeding.")
            return
        
        print("Seeding initial data...")
        
        # Add sample teams (these will be replaced by real FPL data)
        sample_teams = [
            {'team_id': 1, 'name': 'Arsenal', 'short_name': 'ARS'},
            {'team_id': 2, 'name': 'Aston Villa', 'short_name': 'AVL'},
            {'team_id': 3, 'name': 'Brighton', 'short_name': 'BHA'},
            {'team_id': 4, 'name': 'Burnley', 'short_name': 'BUR'},
            {'team_id': 5, 'name': 'Chelsea', 'short_name': 'CHE'},
        ]
        
        for team_data in sample_teams:
            team = Team(**team_data)
            db.session.add(team)
        
        try:
            db.session.commit()
            print(f"Seeded {len(sample_teams)} sample teams.")
        except Exception as e:
            print(f"Error seeding data: {e}")
            db.session.rollback()


def validate_schema(app: Flask) -> None:
    """Validate database schema and constraints."""
    with app.app_context():
        print("\nValidating database schema...")
        
        # Test database connection
        try:
            with db.engine.connect() as conn:
                conn.execute(db.text('SELECT 1'))
            print("✓ Database connection successful")
        except Exception as e:
            print(f"✗ Database connection failed: {e}")
            return
        
        # Check if all tables exist
        inspector = db.inspect(db.engine)
        expected_tables = [
            'teams', 'players', 'fixtures', 'player_past_stats', 
            'player_predictions', 'users', 'user_teams'
        ]
        
        existing_tables = inspector.get_table_names()
        for table in expected_tables:
            if table in existing_tables:
                print(f"✓ Table '{table}' exists")
            else:
                print(f"✗ Table '{table}' missing")
        
        # Verify critical indexes
        if 'players' in existing_tables:
            players_indexes = inspector.get_indexes('players')
            index_names = [idx['name'] for idx in players_indexes]
            
            if 'idx_player_web_name' in index_names:
                print("✓ Critical index 'idx_player_web_name' exists")
            else:
                print("✗ Critical index 'idx_player_web_name' missing")
        
        print("Schema validation completed.")


def main():
    """Main function to set up database."""
    print("FPL AI Optimizer Database Setup")
    print("=" * 40)
    
    # Create Flask app
    app = create_app()
    
    print(f"Using configuration: {app.config.__class__.__name__}")
    print(f"Database URL: {app.config['SQLALCHEMY_DATABASE_URI']}")
    
    # Setup database
    setup_database(app)
    
    # Seed initial data if requested
    if os.environ.get('SEED_DATA', '').lower() == 'true':
        seed_initial_data(app)
    
    # Validate schema
    validate_schema(app)
    
    print("\nDatabase setup completed successfully!")
    print("To fetch FPL data, run: python scripts/fetch_fpl_data.py")


if __name__ == '__main__':
    main()