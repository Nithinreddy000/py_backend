#!/bin/bash

# Script to start the Python backend server for Cloud Run
echo "Starting AI Backend Server on port ${PORT:-8080}..."

# Ensure PORT is set
export PORT=${PORT:-8080}

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

# Start Gunicorn server - use exec to replace the shell process
# This ensures proper signal handling in Cloud Run
echo "Starting Gunicorn server with optimized settings on port ${PORT}..."
exec gunicorn --bind 0.0.0.0:${PORT} \
    --workers 1 \
    --threads 4 \
    --timeout 600 \
    --graceful-timeout 300 \
    --keep-alive 5 \
    app:app 