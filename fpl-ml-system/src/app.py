"""Main application entry point for FPL AI Optimizer."""

import os
from flask import Flask
from src import create_app

# Create Flask application
app = create_app()

if __name__ == '__main__':
    # Development server configuration
    debug = os.environ.get('DEBUG', 'False').lower() in ('true', '1', 'yes')
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '127.0.0.1')
    
    app.run(
        host=host,
        port=port,
        debug=debug,
        threaded=True
    )