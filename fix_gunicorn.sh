#!/bin/bash

# This script modifies Gunicorn settings to fix worker timeout issues
# Run this script on the server where the application is deployed

echo "Fixing Gunicorn worker timeout issues..."

# Environment variables to optimize model loading and TensorFlow
export TF_ENABLE_ONEDNN_OPTS=0
export TF_CPP_MIN_LOG_LEVEL=2
export TF_FORCE_GPU_ALLOW_GROWTH=true
export LAZY_LOAD_MODELS=false
export CORS_ENABLED=true
export PYTHONUNBUFFERED=1

# Find the Gunicorn process
GUNICORN_PID=$(pgrep -f gunicorn)

if [ -z "$GUNICORN_PID" ]; then
  echo "No Gunicorn process found. Starting with fixed settings..."
  
  # Start Gunicorn with improved settings
  gunicorn --bind 0.0.0.0:${PORT:-8080} \
    --workers 2 \
    --threads 8 \
    --timeout 600 \
    --graceful-timeout 300 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --worker-class gthread \
    --preload \
    --log-level info \
    app:app &
    
  echo "Started Gunicorn with PID: $!"
else
  echo "Found Gunicorn process with PID: $GUNICORN_PID"
  echo "Stopping Gunicorn..."
  kill -TERM $GUNICORN_PID
  
  # Wait for process to stop
  sleep 5
  
  # Start Gunicorn with improved settings
  echo "Starting Gunicorn with fixed settings..."
  gunicorn --bind 0.0.0.0:${PORT:-8080} \
    --workers 2 \
    --threads 8 \
    --timeout 600 \
    --graceful-timeout 300 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --worker-class gthread \
    --preload \
    --log-level info \
    app:app &
    
  echo "Started Gunicorn with PID: $!"
fi

echo "Fix completed! Models will now be preloaded and shared between workers." 