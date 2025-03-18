#!/bin/bash

# This script modifies Gunicorn settings to fix worker timeout issues
# Run this script on the server where the application is deployed

echo "Fixing Gunicorn worker timeout issues..."

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
    --log-level info \
    app:app &
    
  echo "Started Gunicorn with PID: $!"
fi

echo "Fix completed!" 