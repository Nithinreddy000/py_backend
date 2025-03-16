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

# Start the Gunicorn server
echo "Starting Gunicorn server..."
gunicorn app:app --config gunicorn_config.py 