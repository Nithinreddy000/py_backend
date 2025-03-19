#!/bin/bash
# Google Cloud Run Entrypoint Script with Flask/Werkzeug Compatibility Fix
# This script patches werkzeug.urls with the url_quote function and starts Gunicorn

# Patch werkzeug
echo "Patching werkzeug.urls for Flask compatibility..."
echo 'from urllib.parse import quote as url_quote' >> /usr/local/lib/python3.9/site-packages/werkzeug/urls.py
echo "Patch applied successfully"

# Verify patch worked
python -c "from werkzeug.urls import url_quote; print('url_quote patch verified')" || echo "Warning: url_quote still not available"

# Set environment variables for improved compatibility
export TF_ENABLE_ONEDNN_OPTS=0
export TF_CPP_MIN_LOG_LEVEL=3
export DISABLE_TENSOR_FLOAT_32_EXECUTION=1
export DISABLE_TRANSFORMERS=true
export CUDA_VISIBLE_DEVICES=-1

# Start application with Gunicorn
echo "Starting application with Gunicorn..."
exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 600 --graceful-timeout 300 --keep-alive 5 --max-requests 1000 --max-requests-jitter 50 --worker-class gthread --log-level info app:app 