#!/bin/bash
# WorldDot Installation Script

set -e  # Exit on error

echo "======================================"
echo "WorldDot Installation"
echo "======================================"
echo ""

# Check Python version
echo "1. Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "   Python $python_version"

if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" 2>/dev/null; then
    echo "   ERROR: Python 3.10+ required"
    exit 1
fi
echo "   ✓ Python version OK"
echo ""

# Create virtual environment
echo "2. Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "   ✓ Virtual environment created"
else
    echo "   ✓ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "3. Activating virtual environment..."
source venv/bin/activate
echo "   ✓ Virtual environment activated"
echo ""

# Upgrade pip
echo "4. Upgrading pip..."
pip install --upgrade pip --quiet
echo "   ✓ Pip upgraded"
echo ""

# Install dependencies
echo "5. Installing dependencies..."
pip install -r requirements.txt --quiet
echo "   ✓ Dependencies installed"
echo ""

# Download geographic data
echo "6. Downloading geographic data..."
python3 src/mapdata.py
echo ""

# Verify installation
echo "7. Verifying installation..."
python3 -c "
import sys
try:
    import numpy
    import shapely
    import geopandas
    import pyproj
    print('   ✓ All dependencies verified')
except ImportError as e:
    print(f'   ERROR: {e}')
    sys.exit(1)
"
echo ""

# Check geographic data
if [ -f "data/world.geojson" ]; then
    echo "   ✓ Geographic data verified"
else
    echo "   WARNING: Geographic data not found"
fi
echo ""

echo "======================================"
echo "Installation Complete!"
echo "======================================"
echo ""
echo "To launch WorldDot, run:"
echo "  python3 worlddot.py"
echo ""
echo "For help:"
echo "  python3 worlddot.py --help"
echo ""
echo "For debug mode:"
echo "  python3 worlddot.py --debug"
echo ""
