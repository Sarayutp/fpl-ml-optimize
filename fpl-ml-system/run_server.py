#!/usr/bin/env python3
"""Simple server runner for FPL AI Optimizer."""

import sys
import os

# Add project to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from production_app import create_production_app

app = create_production_app()

if __name__ == '__main__':
    # Use Werkzeug directly for more reliable serving
    from werkzeug.serving import run_simple
    
    print("🚀 Starting FPL AI Optimizer Server...")
    print("📡 Server will be available at: http://localhost:5001")
    print("🏠 Dashboard: http://localhost:5001/")
    print("⚽ Optimizer: http://localhost:5001/optimizer") 
    print("🔍 Scouting: http://localhost:5001/scouting")
    print("💚 Health Check: http://localhost:5001/api/health")
    print("🎯 Optimization API: POST /api/optimize")
    print()
    
    try:
        run_simple('localhost', 5001, app, 
                  use_debugger=True,
                  use_reloader=True,
                  threaded=True)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
    except Exception as e:
        print(f"❌ Server error: {e}")