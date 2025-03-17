#!/bin/bash
set -e

echo "Running startup script..."

# Install required packages
echo "Installing dependencies..."
pip install -r requirements.txt

# Skip the heavy import checks which were causing memory issues
echo "Skipping import checks due to memory constraints..."

# Create required directories
echo "Setting up directories..."
mkdir -p uploads
mkdir -p models/z-anatomy/output
mkdir -p mesh_data
mkdir -p temp_fixes

# Only download the essential small model to conserve memory
echo "Downloading minimal model..."
python -c "
import os
import torch
print('Downloading minimal model...')
model_path = 'yolov8n.pt'
if not os.path.exists(model_path):
    torch.hub.download_url_to_file(
        'https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt',
        model_path
    )
    print(f'Downloaded {model_path}')
else:
    print(f'{model_path} already exists')
"

# Set any required environment variables
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Make sure PORT is set - Render sets this, but just to be safe
if [ -z "${PORT}" ]; then
  export PORT=10000
  echo "PORT not set, defaulting to 10000"
else
  echo "Using PORT: ${PORT}"
fi

# Print debugging information
echo "Environment:"
echo "- PYTHONPATH: $PYTHONPATH"
echo "- PORT: $PORT"
echo "- Current directory: $(pwd)"

# Start the server using our simplified entry point
echo "Starting server..."
gunicorn render_app:app --bind 0.0.0.0:$PORT --workers 1 --timeout 300 --log-level debug 