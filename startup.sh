#!/bin/bash
set -e

echo "Running startup script..."

# Install required packages
echo "Installing dependencies..."
pip install -r requirements.txt

# Create required directories
echo "Setting up directories..."
mkdir -p uploads
mkdir -p models/z-anatomy/output
mkdir -p mesh_data
mkdir -p temp_fixes

# Download required models
echo "Downloading models..."
python download_models.py

# Start the Gunicorn server
echo "Starting Gunicorn server..."
gunicorn app:app --config gunicorn_config.py 