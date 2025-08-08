"""Flask application factory for FPL AI Optimizer."""

import logging
import os
from logging.handlers import RotatingFileHandler

from flask import Flask, render_template
from flask_migrate import Migrate
import click

# Simple cache implementation for now
class SimpleCache:
    def __init__(self, app=None):
        self.cache_data = {}
        
    def get(self, key):
        return self.cache_data.get(key)
        
    def set(self, key, value, timeout=None):
        self.cache_data[key] = value
        
    def clear(self):
        self.cache_data.clear()

from .config import get_config
from .models.db_models import db


def create_app(config_name=None):
    """
    Flask application factory.
    
    Args:
        config_name: Configuration name ('development', 'testing', 'production')
        
    Returns:
        Configured Flask application instance
    """
    # Create Flask instance
    app = Flask(__name__)
    
    # Load configuration
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    config = get_config(config_name)
    app.config.from_object(config)
    
    # Initialize extensions
    db.init_app(app)
    migrate = Migrate(app, db)
    cache = SimpleCache(app)
    
    # Initialize services with app context
    from .services.data_service import DataService
    from .services.prediction_service import PredictionService
    from .services.optimization_service import OptimizationService
    from .services.reasoning_service import ReasoningService
    
    data_service = DataService(app, cache)
    prediction_service = PredictionService(app)
    optimization_service = OptimizationService(app)
    reasoning_service = ReasoningService(app)
    
    # Store services in app context for easy access
    app.data_service = data_service
    app.prediction_service = prediction_service
    app.optimization_service = optimization_service
    app.reasoning_service = reasoning_service
    app.cache = cache
    
    # Register blueprints
    from .views.dashboard import dashboard_bp
    from .views.optimizer import optimizer_bp
    from .views.scouting import scouting_bp
    from .views.api import api_bp
    
    app.register_blueprint(dashboard_bp, url_prefix='/')
    app.register_blueprint(optimizer_bp, url_prefix='/optimizer')
    app.register_blueprint(scouting_bp, url_prefix='/scouting')
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(Exception)
    def handle_exception(e):
        # Log the exception
        app.logger.error(f"Unhandled exception: {e}", exc_info=True)
        
        # If it's an HTTP exception, let it pass through
        if hasattr(e, 'code'):
            return e
        
        # Otherwise treat it as 500
        db.session.rollback()
        return render_template('errors/500.html'), 500
    
    # Context processors
    @app.context_processor
    def inject_debug():
        return dict(debug=app.debug)
    
    @app.context_processor
    def inject_config():
        return dict(
            app_name="FPL AI Optimizer",
            version="1.0.0"
        )
    
    # Template filters
    @app.template_filter('currency')
    def currency_filter(value):
        """Format currency values."""
        if value is None:
            return "£0.0M"
        return f"£{value:.1f}M"
    
    @app.template_filter('points')
    def points_filter(value):
        """Format points values."""
        if value is None:
            return "0"
        return f"{value:.1f}"
    
    # CLI commands
    @app.cli.command()
    def init_db():
        """Initialize the database."""
        db.create_all()
        click.echo('Database initialized.')
    
    @app.cli.command()
    def fetch_data():
        """Fetch data from FPL API."""
        with app.app_context():
            try:
                stats = data_service.update_database_from_api()
                click.echo(f"Data fetch completed: {stats}")
            except Exception as e:
                click.echo(f"Data fetch failed: {e}")
    
    # Setup logging
    if not app.testing:
        setup_logging(app)
    
    return app


def setup_logging(app):
    """Set up logging configuration."""
    if not app.debug and not app.testing:
        # Create logs directory if it doesn't exist
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        # Set up file logging
        file_handler = RotatingFileHandler(
            'logs/app.log', 
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('FPL AI Optimizer startup')
    
    # Set logging level based on config
    log_level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO').upper(), logging.INFO)
    app.logger.setLevel(log_level)