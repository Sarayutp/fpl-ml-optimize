#!/usr/bin/env python3
"""System information script for debugging and support - สร้างรายงานข้อมูลระบบ"""

import os
import sys
import platform
import subprocess
from pathlib import Path
from datetime import datetime
import json

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def get_system_info():
    """Get basic system information."""
    return {
        "timestamp": datetime.now().isoformat(),
        "platform": platform.platform(),
        "python_version": sys.version,
        "architecture": platform.architecture(),
        "processor": platform.processor(),
        "hostname": platform.node(),
        "username": os.getenv("USER", "unknown")
    }


def get_python_packages():
    """Get installed Python packages."""
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "list"], 
                              capture_output=True, text=True)
        return result.stdout
    except Exception as e:
        return f"Error getting packages: {e}"


def check_project_structure():
    """Check project directory structure."""
    expected_dirs = [
        "src", "src/models", "src/services", "src/views", "src/templates",
        "tests", "scripts", "logs", "data", "models"
    ]
    
    expected_files = [
        "requirements.txt", ".env.example", "src/config.py",
        "src/models/db_models.py", "src/models/data_models.py"
    ]
    
    structure_check = {
        "directories": {},
        "files": {}
    }
    
    for dir_path in expected_dirs:
        full_path = project_root / dir_path
        structure_check["directories"][dir_path] = full_path.exists()
    
    for file_path in expected_files:
        full_path = project_root / file_path
        structure_check["files"][file_path] = full_path.exists()
    
    return structure_check


def get_database_info():
    """Get database information."""
    db_info = {}
    
    try:
        from src import create_app
        from src.models.db_models import db
        
        app = create_app('development')
        with app.app_context():
            # Check database connection
            try:
                with db.engine.connect() as conn:
                    conn.execute(db.text('SELECT 1'))
                db_info["connection"] = "OK"
            except Exception as e:
                db_info["connection"] = f"Error: {e}"
            
            # Check tables
            try:
                inspector = db.inspect(db.engine)
                db_info["tables"] = inspector.get_table_names()
            except Exception as e:
                db_info["tables"] = f"Error: {e}"
            
            # Get database file info
            db_file = project_root / "data" / "fpl.db"
            if db_file.exists():
                stat = db_file.stat()
                db_info["file_size_mb"] = round(stat.st_size / (1024 * 1024), 2)
                db_info["last_modified"] = datetime.fromtimestamp(stat.st_mtime).isoformat()
            else:
                db_info["file_exists"] = False
                
    except Exception as e:
        db_info["error"] = str(e)
    
    return db_info


def get_ml_models_info():
    """Get ML models information."""
    models_info = {}
    models_dir = project_root / "models"
    
    if models_dir.exists():
        models_info["directory_exists"] = True
        models_info["files"] = []
        
        for model_file in models_dir.glob("*.pkl"):
            stat = model_file.stat()
            models_info["files"].append({
                "name": model_file.name,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
    else:
        models_info["directory_exists"] = False
    
    return models_info


def get_logs_info():
    """Get logs information."""
    logs_info = {}
    logs_dir = project_root / "logs"
    
    if logs_dir.exists():
        logs_info["directory_exists"] = True
        logs_info["files"] = []
        
        for log_file in logs_dir.glob("*.log"):
            stat = log_file.stat()
            logs_info["files"].append({
                "name": log_file.name,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
            
        # Get recent log entries
        app_log = logs_dir / "app.log"
        if app_log.exists():
            try:
                with open(app_log, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    logs_info["recent_entries"] = lines[-10:] if lines else []
            except Exception as e:
                logs_info["recent_entries"] = f"Error reading logs: {e}"
    else:
        logs_info["directory_exists"] = False
    
    return logs_info


def get_environment_info():
    """Get environment variables (safe ones only)."""
    safe_env_vars = [
        "FLASK_ENV", "DATABASE_URL", "FPL_API_BASE_URL", 
        "CACHE_TTL", "LOG_LEVEL", "PYTHONPATH"
    ]
    
    env_info = {}
    for var in safe_env_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive parts
            if "URL" in var and "://" in value:
                parts = value.split("://")
                if len(parts) > 1:
                    env_info[var] = f"{parts[0]}://[masked]"
                else:
                    env_info[var] = "[masked]"
            else:
                env_info[var] = value
        else:
            env_info[var] = "Not set"
    
    return env_info


def check_network_connectivity():
    """Check network connectivity to FPL API."""
    connectivity = {}
    
    try:
        import requests
        response = requests.get(
            "https://fantasy.premierleague.com/api/bootstrap-static/",
            timeout=10
        )
        connectivity["fpl_api"] = {
            "status": "OK",
            "status_code": response.status_code,
            "response_size": len(response.content)
        }
    except Exception as e:
        connectivity["fpl_api"] = {
            "status": "Error",
            "error": str(e)
        }
    
    # Check localhost
    try:
        import requests
        response = requests.get("http://localhost:5000/api/health", timeout=5)
        connectivity["local_api"] = {
            "status": "OK",
            "status_code": response.status_code
        }
    except Exception as e:
        connectivity["local_api"] = {
            "status": "Error", 
            "error": str(e)
        }
    
    return connectivity


def run_basic_tests():
    """Run basic functionality tests."""
    tests = {}
    
    # Test imports
    try:
        from src.models.data_models import PlayerStats
        from src.models.db_models import Player
        tests["model_imports"] = "OK"
    except Exception as e:
        tests["model_imports"] = f"Error: {e}"
    
    # Test services
    try:
        from src.services.data_service import DataService
        from src.services.prediction_service import PredictionService
        tests["service_imports"] = "OK"
    except Exception as e:
        tests["service_imports"] = f"Error: {e}"
    
    # Test configuration
    try:
        from src.config import get_config
        config = get_config('development')
        tests["configuration"] = "OK"
    except Exception as e:
        tests["configuration"] = f"Error: {e}"
    
    return tests


def generate_report():
    """Generate comprehensive system report."""
    print("🔍 FPL AI Optimizer - System Information Report")
    print("=" * 60)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    report = {}
    
    # System Information
    print("\n📊 SYSTEM INFORMATION")
    print("-" * 40)
    system_info = get_system_info()
    report["system"] = system_info
    
    for key, value in system_info.items():
        if key != "python_version":
            print(f"{key.replace('_', ' ').title()}: {value}")
        else:
            # Format Python version nicely
            version_line = value.split('\n')[0]
            print(f"Python Version: {version_line}")
    
    # Project Structure
    print("\n📁 PROJECT STRUCTURE")
    print("-" * 40)
    structure = check_project_structure()
    report["structure"] = structure
    
    print("Directories:")
    for dir_name, exists in structure["directories"].items():
        status = "✅" if exists else "❌"
        print(f"  {status} {dir_name}")
    
    print("\nFiles:")
    for file_name, exists in structure["files"].items():
        status = "✅" if exists else "❌"
        print(f"  {status} {file_name}")
    
    # Environment Variables
    print("\n🔧 ENVIRONMENT CONFIGURATION")
    print("-" * 40)
    env_info = get_environment_info()
    report["environment"] = env_info
    
    for var, value in env_info.items():
        print(f"{var}: {value}")
    
    # Database Information
    print("\n🗄️  DATABASE INFORMATION")
    print("-" * 40)
    db_info = get_database_info()
    report["database"] = db_info
    
    if "error" in db_info:
        print(f"❌ Database Error: {db_info['error']}")
    else:
        print(f"Connection: {db_info.get('connection', 'Unknown')}")
        if isinstance(db_info.get('tables'), list):
            print(f"Tables: {len(db_info['tables'])} found")
            for table in db_info['tables']:
                print(f"  - {table}")
        if "file_size_mb" in db_info:
            print(f"Database Size: {db_info['file_size_mb']} MB")
            print(f"Last Modified: {db_info['last_modified']}")
    
    # ML Models Information
    print("\n🤖 MACHINE LEARNING MODELS")
    print("-" * 40)
    ml_info = get_ml_models_info()
    report["ml_models"] = ml_info
    
    if ml_info["directory_exists"]:
        if ml_info["files"]:
            print(f"Found {len(ml_info['files'])} model files:")
            for model in ml_info["files"]:
                print(f"  - {model['name']} ({model['size_mb']} MB)")
        else:
            print("⚠️  No model files found - run 'python scripts/train_models.py'")
    else:
        print("❌ Models directory doesn't exist")
    
    # Logs Information
    print("\n📝 LOGS INFORMATION")
    print("-" * 40)
    logs_info = get_logs_info()
    report["logs"] = logs_info
    
    if logs_info["directory_exists"]:
        if logs_info["files"]:
            print(f"Found {len(logs_info['files'])} log files:")
            for log in logs_info["files"]:
                print(f"  - {log['name']} ({log['size_mb']} MB)")
        else:
            print("No log files found")
    else:
        print("❌ Logs directory doesn't exist")
    
    # Network Connectivity
    print("\n🌐 NETWORK CONNECTIVITY")
    print("-" * 40)
    connectivity = check_network_connectivity()
    report["connectivity"] = connectivity
    
    for service, info in connectivity.items():
        service_name = service.replace('_', ' ').title()
        if info["status"] == "OK":
            print(f"✅ {service_name}: {info['status']}")
        else:
            print(f"❌ {service_name}: {info['error']}")
    
    # Basic Tests
    print("\n🧪 BASIC FUNCTIONALITY TESTS")
    print("-" * 40)
    tests = run_basic_tests()
    report["tests"] = tests
    
    for test_name, result in tests.items():
        test_display = test_name.replace('_', ' ').title()
        if result == "OK":
            print(f"✅ {test_display}: {result}")
        else:
            print(f"❌ {test_display}: {result}")
    
    # Python Packages
    print("\n📦 INSTALLED PACKAGES")
    print("-" * 40)
    packages = get_python_packages()
    report["packages"] = packages
    
    if "Error" not in packages:
        package_lines = packages.split('\n')
        print(f"Total packages: {len([l for l in package_lines if l.strip()])}")
        
        # Show key packages
        key_packages = ['flask', 'pandas', 'numpy', 'scikit-learn', 'xgboost', 'pulp', 'pydantic', 'sqlalchemy']
        print("\nKey packages:")
        for line in package_lines:
            if any(pkg in line.lower() for pkg in key_packages):
                print(f"  - {line}")
    else:
        print(f"❌ {packages}")
    
    # Summary
    print("\n📋 SUMMARY")
    print("-" * 40)
    
    issues = []
    
    # Check for common issues
    if not structure["directories"].get("data", False):
        issues.append("Data directory missing")
    
    if not structure["directories"].get("models", False):
        issues.append("Models directory missing")
    
    if "Error" in str(db_info.get("connection", "")):
        issues.append("Database connection error")
    
    if not ml_info.get("files", []):
        issues.append("No ML models found")
    
    if connectivity["fpl_api"]["status"] != "OK":
        issues.append("FPL API connectivity issue")
    
    if any("Error" in str(result) for result in tests.values()):
        issues.append("Basic functionality tests failed")
    
    if issues:
        print("⚠️  Issues found:")
        for issue in issues:
            print(f"  - {issue}")
        print("\n💡 Recommendations:")
        print("  1. Run: python scripts/setup_database.py")
        print("  2. Run: python scripts/fetch_fpl_data.py") 
        print("  3. Run: python scripts/train_models.py")
        print("  4. Check internet connection")
        print("  5. Review USER_GUIDE_TH.md for troubleshooting")
    else:
        print("✅ System appears to be working correctly!")
        print("🚀 Ready to run: flask run")
    
    # Save report to file
    report_file = project_root / "system_report.json"
    try:
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        print(f"\n💾 Full report saved to: {report_file}")
    except Exception as e:
        print(f"\n⚠️  Could not save report file: {e}")
    
    print("\n" + "=" * 60)
    print("Report generation complete!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        generate_report()
    except KeyboardInterrupt:
        print("\n⚠️  Report generation cancelled")
    except Exception as e:
        print(f"\n🚨 Error generating report: {e}")
        import traceback
        traceback.print_exc()