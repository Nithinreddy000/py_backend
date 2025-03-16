#!/bin/bash
set -e

echo "Running startup script..."

# Download required models
echo "Downloading models..."
python download_models.py

# Start the Gunicorn server
echo "Starting Gunicorn server..."
gunicorn app:app --config gunicorn_config.py 