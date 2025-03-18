#!/bin/bash
# Script to run the Flask application with necessary setup

# Print application information
echo "Starting 3D Injury Visualization Backend"
echo "========================================"

# Run the ultralytics fix script first
echo "Fixing ultralytics settings..."
python fix_ultralytics.py

# Check if fix was successful
if [ $? -ne 0 ]; then
    echo "Warning: Failed to fix ultralytics settings, application may encounter errors."
fi

# Set environment variables if not already set
export PORT=${PORT:-8080}
export FLASK_APP=${FLASK_APP:-app.py}
export FLASK_DEBUG=${FLASK_DEBUG:-0}

# Check if we're running in a container
if [ -f /.dockerenv ]; then
    echo "Running in Docker container"
    # Use gunicorn in container environment
    exec gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 8 --timeout 300 app:app
else
    echo "Running in local environment"
    # Use Flask's built-in server for local development
    exec flask run --host=0.0.0.0 --port=$PORT
fi 