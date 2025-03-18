#!/bin/bash

# This script preloads ML models to avoid runtime downloads
# Run this script on the server where the application is deployed
# to improve startup performance

echo "Preloading ML models for faster startup..."

# Create model directories if they don't exist
mkdir -p /app/models/yolo
mkdir -p /app/models/easyocr
mkdir -p /app/models/z-anatomy/output
mkdir -p /app/fallback_models
mkdir -p /root/.config/ultralytics
mkdir -p /root/.EasyOCR
mkdir -p /root/.cache/torch

# Set proper permissions
chmod -R 777 /root/.config/ultralytics
chmod -R 777 /root/.EasyOCR
chmod -R 777 /app/models

# Download YOLO models if not already downloaded
if [ ! -f "/root/.config/ultralytics/models/yolov8n-pose.pt" ]; then
  echo "Downloading YOLO pose model..."
  python -c "from ultralytics import YOLO; YOLO('yolov8n-pose.pt')" || echo "Failed to download YOLO pose model"
fi

if [ ! -f "/root/.config/ultralytics/models/yolov8n.pt" ]; then
  echo "Downloading YOLO detection model..."
  python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')" || echo "Failed to download YOLO detection model"
fi

# Download EasyOCR models if not already downloaded
if [ ! -d "/app/models/easyocr" ] || [ -z "$(ls -A /app/models/easyocr)" ]; then
  echo "Downloading EasyOCR models..."
  python -c "import easyocr; reader = easyocr.Reader(['en'], model_storage_directory='/app/models/easyocr', download_enabled=True)" || echo "Failed to download EasyOCR models"
fi

# Set environment variables for the models
echo "Setting environment variables for model paths..."
export EASYOCR_MODULE_PATH=/app/models/easyocr
export YOLO_MODEL_PATH=/root/.config/ultralytics/models

# Create a file to indicate models are preloaded
touch /app/models/.preloaded

echo "Models preloaded successfully!"
echo "The application should now start faster and avoid runtime downloads."

# Restart the application if Gunicorn is running
GUNICORN_PID=$(pgrep -f gunicorn)

if [ -n "$GUNICORN_PID" ]; then
  echo "Found Gunicorn process with PID: $GUNICORN_PID"
  echo "Would you like to restart the application now? (y/n)"
  read -r answer
  
  if [ "$answer" = "y" ] || [ "$answer" = "Y" ]; then
    echo "Stopping Gunicorn..."
    kill -TERM $GUNICORN_PID
    
    # Wait for process to stop
    sleep 5
    
    # Start Gunicorn with standard settings (adjust as needed)
    echo "Starting Gunicorn with preloaded models..."
    cd /app
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
    echo "The application will use preloaded models on next restart."
  fi
else
  echo "No Gunicorn process found. The application will use preloaded models on next startup."
fi 