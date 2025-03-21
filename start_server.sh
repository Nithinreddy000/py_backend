#!/bin/bash

# Script to start the Python backend server with monitoring
echo "Starting AI Backend Server..."

# Set environment variables for memory optimization
export MALLOC_ARENA_MAX=2
export TF_FORCE_GPU_ALLOW_GROWTH=true
export TF_CPP_MIN_LOG_LEVEL=2
export CUDA_VISIBLE_DEVICES="-1"
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1

# Set Python garbage collection threshold
export PYTHONUNBUFFERED=1
export PYTHONGC="threshold=700000"

# Install psutil if not already installed (needed for monitor.py)
pip install psutil --quiet || echo "Failed to install psutil, worker monitoring may not function"

# Start worker monitoring script in background if it exists
if [ -f "monitor.py" ]; then
    echo "Starting worker monitor..."
    python monitor.py &
    MONITOR_PID=$!
    echo "Monitor started with PID $MONITOR_PID"
fi

# Function to start the server
start_server() {
    echo "Starting Gunicorn server with optimized settings..."
    gunicorn --bind 0.0.0.0:$PORT \
        --workers 1 \
        --threads 4 \
        --timeout 600 \
        --graceful-timeout 300 \
        --keep-alive 5 \
        --max-requests 10 \
        --max-requests-jitter 5 \
        --worker-class=gevent \
        --preload \
        app:app
    
    # Get the exit code
    EXIT_CODE=$?
    
    # If server exited with an error, log it
    if [ $EXIT_CODE -ne 0 ]; then
        echo "Server exited with code $EXIT_CODE at $(date)"
        return 1
    fi
    
    return 0
}

# Main loop - restart server up to 5 times if it crashes
MAX_RETRIES=5
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    # Start the server
    start_server
    
    # If server exited cleanly, break the loop
    if [ $? -eq 0 ]; then
        echo "Server stopped cleanly at $(date)"
        break
    fi
    
    # Increment retry count
    RETRY_COUNT=$((RETRY_COUNT + 1))
    
    # If we've reached max retries, exit
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        echo "Server failed to start after $MAX_RETRIES attempts. Exiting."
        exit 1
    fi
    
    # Wait before restarting
    WAIT_TIME=$((RETRY_COUNT * 5))
    echo "Waiting $WAIT_TIME seconds before restarting server (attempt $RETRY_COUNT of $MAX_RETRIES)..."
    sleep $WAIT_TIME
done

# If we get here, the server has stopped - kill the monitor
if [ ! -z "$MONITOR_PID" ]; then
    echo "Stopping monitor process (PID $MONITOR_PID)..."
    kill $MONITOR_PID || true
fi

echo "Server process complete" 