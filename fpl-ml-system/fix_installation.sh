#!/bin/bash

echo "🔧 FPL AI Optimizer - Fix Installation Script"
echo "=============================================="

# Check if virtual environment is active
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✅ Virtual environment is active: $VIRTUAL_ENV"
else
    echo "⚠️  Activating virtual environment..."
    source venv/bin/activate
fi

echo ""
echo "🛠️  Step 1: Upgrade build tools..."
pip install --upgrade pip setuptools wheel

echo ""
echo "🛠️  Step 2: Install build dependencies..."
pip install Cython setuptools-scm build

echo ""
echo "🛠️  Step 3: Install core dependencies first..."
pip install numpy==1.26.4  # Use newer version compatible with Python 3.12
pip install pandas>=2.1.0
pip install scikit-learn>=1.3.0

echo ""
echo "🛠️  Step 4: Install XGBoost with specific method..."
# XGBoost might need special handling on macOS
pip install xgboost>=2.0.0 --no-cache-dir

echo ""
echo "🛠️  Step 5: Install remaining dependencies..."
pip install -r requirements-updated.txt --no-cache-dir

echo ""
echo "🔍 Step 6: Verify installation..."
python -c "
import sys
print(f'Python version: {sys.version}')

try:
    import numpy
    print(f'✅ NumPy {numpy.__version__}')
except ImportError as e:
    print(f'❌ NumPy: {e}')

try:
    import pandas
    print(f'✅ Pandas {pandas.__version__}')
except ImportError as e:
    print(f'❌ Pandas: {e}')

try:
    import sklearn
    print(f'✅ Scikit-learn {sklearn.__version__}')
except ImportError as e:
    print(f'❌ Scikit-learn: {e}')

try:
    import xgboost
    print(f'✅ XGBoost {xgboost.__version__}')
except ImportError as e:
    print(f'❌ XGBoost: {e}')

try:
    import flask
    print(f'✅ Flask {flask.__version__}')
except ImportError as e:
    print(f'❌ Flask: {e}')

try:
    import pulp
    print(f'✅ PuLP {pulp.__version__}')
except ImportError as e:
    print(f'❌ PuLP: {e}')
"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Core dependencies verified successfully!"
    echo ""
    echo "🚀 Next steps:"
    echo "1. Run: python scripts/setup_database.py"
    echo "2. Run: python scripts/quick_start.py"
    echo "3. Run: flask run"
else
    echo ""
    echo "❌ Some dependencies failed to install properly"
    echo "Please check the error messages above"
fi

echo ""
echo "=============================================="