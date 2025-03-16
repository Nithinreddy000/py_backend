#!/bin/bash
set -e

echo "Running startup script..."

# Install required packages
echo "Installing dependencies..."
pip install -r requirements.txt

# Verify dependencies are installed
echo "Verifying dependencies..."
python check_imports.py || {
  echo "Some dependencies failed to import. Installing key packages explicitly..."
  pip install flask==2.0.1 flask-cors==3.0.10 PyMuPDF>=1.20.0 ultralytics>=8.0.0 torch>=2.0.0
  
  # Try the imports check again
  python check_imports.py || {
    echo "Warning: Import check still failing, but continuing startup..."
  }
}

# Create required directories
echo "Setting up directories..."
mkdir -p uploads
mkdir -p models/z-anatomy/output
mkdir -p mesh_data
mkdir -p temp_fixes

# Download required models
echo "Downloading models..."
python download_models.py

# Set any required environment variables
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Make sure PORT is set - Render sets this, but just to be safe
if [ -z "${PORT}" ]; then
  export PORT=8000
  echo "PORT not set, defaulting to 8000"
else
  echo "Using PORT: ${PORT}"
fi

# Print debugging information
echo "Environment:"
echo "- PYTHONPATH: $PYTHONPATH"
echo "- PORT: $PORT"
echo "- Current directory: $(pwd)"
echo "- Files in current directory: $(ls -la)"

# Start the Gunicorn server with proper port binding
echo "Starting Gunicorn server..."
gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --timeout 300 