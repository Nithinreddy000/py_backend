#!/bin/bash

# This script fixes the missing blinker dependency for Sentry SDK's Flask integration
# Run this script on the server where the application is deployed if you encounter 
# "sentry_sdk.integrations.DidNotEnable: blinker is not installed" errors

echo "Fixing Sentry SDK Flask integration issue..."

# Install blinker package
pip install blinker==1.6.2

# Check if the package was installed correctly
if python -c "import blinker; print(f'Blinker version: {blinker.__version__}')" 2>/dev/null; then
  echo "✅ Blinker installed successfully!"
else
  echo "❌ Failed to install blinker. Please check pip and network connectivity."
  exit 1
fi

# Find and restart Gunicorn processes (if they exist)
GUNICORN_PID=$(pgrep -f gunicorn)

if [ -n "$GUNICORN_PID" ]; then
  echo "Found Gunicorn process with PID: $GUNICORN_PID"
  echo "Stopping Gunicorn..."
  kill -TERM $GUNICORN_PID
  
  # Wait for process to stop
  sleep 5
  
  # Check if Gunicorn is configured to auto-restart
  # If not, we'll need to restart it manually
  NEW_GUNICORN_PID=$(pgrep -f gunicorn)
  
  if [ -z "$NEW_GUNICORN_PID" ]; then
    echo "Gunicorn didn't auto-restart. Starting it manually..."
    cd /app  # Assuming the app is in /app
    
    # Start Gunicorn with standard settings (adjust as needed)
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
    echo "Gunicorn auto-restarted with PID: $NEW_GUNICORN_PID"
  fi
else
  echo "No Gunicorn process found. The application will use the blinker package on next startup."
fi

echo "Fix completed! Sentry SDK should now work correctly with Flask." 