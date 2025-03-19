FROM python:3.9-slim

WORKDIR /app

# Copy requirements file first for better caching
COPY requirements.txt .

# Install required system dependencies with enhanced video processing capabilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    curl \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    ffmpeg \
    git \
    xvfb \
    xauth \
    mesa-utils \
    libgl1 \
    libgles2 \
    libosmesa6 \
    wget \
    unzip \
    # Video processing optimization packages
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libavfilter-dev \
    libavutil-dev \
    # Performance optimizations
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libv4l-dev \
    libx264-dev \
    libx265-dev \
    libvpx-dev \
    libwebp-dev \
    # Additional dependencies for faster video processing
    libopenexr-dev \
    libopencv-dev \
    # Ensure pip is installed for model installation
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Create models directory structure before running preload
RUN mkdir -p models/z-anatomy models/z-anatomy/output fallback_models

# Copy just requirements.txt first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir numpy==1.24.3 && \
    pip install --no-cache-dir opencv-contrib-python-headless==4.7.0.72 && \
    pip install --no-cache-dir -r requirements.txt && \
    # Install specific version of ultralytics known to be compatible with pose models
    pip install --no-cache-dir ultralytics==8.0.196 && \
    # Install specific version of easyocr
    pip install --no-cache-dir easyocr==1.6.2 && \
    # Set env var to prevent auto-download
    echo "export EASYOCR_DOWNLOAD_ENABLED=False" >> /root/.bashrc && \
    # Add the missing imports for model initialization
    pip install importlib_metadata pkg_resources

# Install FFmpeg directly from default repositories
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libavcodec-extra \
    libavfilter-extra \
    && rm -rf /var/lib/apt/lists/*

# Create model directories and prefetch all required models
RUN mkdir -p /app/models/z-anatomy /app/models/z-anatomy/output /app/fallback_models

# Download YOLOv8 models with retry logic and better error handling
RUN for i in 1 2 3; do \
      echo "Download attempt $i for YOLOv8 models"; \
      mkdir -p /app/models && \
      # Base models (detection) \
      wget -q --retry-connrefused --waitretry=5 --read-timeout=30 --timeout=30 -t 3 -O /app/models/yolov8n.pt https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt && \
      wget -q --retry-connrefused --waitretry=5 --read-timeout=30 --timeout=30 -t 3 -O /app/models/yolov8s.pt https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8s.pt && \
      # Pose models \
      wget -q --retry-connrefused --waitretry=5 --read-timeout=30 --timeout=30 -t 3 -O /app/models/yolov8n-pose.pt https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n-pose.pt && \
      # Only if previous download succeeded, get additional models \
      if [ -s /app/models/yolov8n-pose.pt ]; then \
        # Use a different approach for ONNX models with specific version URLs
        wget -q --retry-connrefused --waitretry=5 --read-timeout=30 --timeout=30 -t 3 -O /app/models/yolov8s-pose.pt https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8s-pose.pt || echo "Optional model download failed"; \
        
        # Try different URLs for ONNX files
        for onnx_url in \
          "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.onnx" \
          "https://github.com/ultralytics/yolov5/releases/download/v7.0/yolov8n.onnx" \
          "https://ultralytics.com/assets/yolov8n.onnx"; \
        do \
          echo "Trying ONNX URL: $onnx_url" && \
          wget -q --retry-connrefused --waitretry=5 --read-timeout=30 --timeout=30 -t 3 -O /app/models/yolov8n.onnx "$onnx_url" && \
          if [ -s /app/models/yolov8n.onnx ]; then \
            echo "Successfully downloaded yolov8n.onnx"; \
            break; \
          fi; \
        done; \
        
        # If ONNX file still empty, create dummy file
        if [ ! -s /app/models/yolov8n.onnx ]; then \
          echo "Creating placeholder ONNX files"; \
          echo "Placeholder" > /app/models/yolov8n.onnx; \
          echo "Placeholder" > /app/models/yolov8s.onnx; \
          echo "Placeholder" > /app/models/yolov8n-pose.onnx; \
          echo "Placeholder" > /app/models/yolov8s-pose.onnx; \
        fi; \
      fi; \
      # Check if essential models were downloaded successfully \
      if [ -s /app/models/yolov8n.pt ] && [ -s /app/models/yolov8n-pose.pt ]; then \
        echo "Essential models downloaded successfully"; \
        ls -la /app/models/; \
        break; \
      else \
        echo "Download failed, retrying..."; \
        if [ $i -eq 3 ]; then \
          echo "ERROR: Failed to download essential models after 3 attempts"; \
          exit 1; \
        fi; \
        sleep 5; \
      fi; \
    done

# Install EasyOCR models - FIXED VERSION with direct S3 URLs not GitHub
RUN apt-get update && \
    # Install curl for reliable downloads
    apt-get install -y curl && \
    # Create the model directory
    mkdir -p /app/models && \
    # Download EasyOCR models from S3 directly
    curl -L -o /app/models/craft_mlt_25k.pth https://easyocr.s3.us-east-2.amazonaws.com/craft_mlt_25k.pth && \
    curl -L -o /app/models/english_g2.pth https://easyocr.s3.us-east-2.amazonaws.com/english_g2.pth && \
    # Verify models exist and aren't empty
    ls -la /app/models/ && \
    echo "craft_mlt_25k.pth size: $(stat -c %s /app/models/craft_mlt_25k.pth)" && \
    echo "english_g2.pth size: $(stat -c %s /app/models/english_g2.pth)" && \
    # If either model is missing or empty, fail the build
    if [ ! -s /app/models/craft_mlt_25k.pth ] || [ ! -s /app/models/english_g2.pth ]; then \
      echo "ERROR: EasyOCR models failed to download. Build failed!" && \
      exit 1; \
    fi && \
    # Clean up
    apt-get remove -y curl && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# Create a script to install Blender if it's missing
RUN echo '#!/bin/bash\n\
echo "Installing Blender..."\n\
apt-get update\n\
apt-get install -y blender\n\
if ! command -v blender &> /dev/null; then\n\
  echo "Failed to install Blender using apt, trying alternative download"\n\
  apt-get install -y wget xz-utils\n\
  cd /tmp\n\
  wget -q https://download.blender.org/release/Blender3.6/blender-3.6.1-linux-x64.tar.xz\n\
  tar -xf blender-3.6.1-linux-x64.tar.xz\n\
  mv blender-3.6.1-linux-x64 /opt/blender\n\
  ln -s /opt/blender/blender /usr/local/bin/blender\n\
  rm blender-3.6.1-linux-x64.tar.xz\n\
  apt-get remove -y wget xz-utils\n\
  apt-get autoremove -y\n\
fi\n\
echo "Blender installation complete"\n\
blender --version\n\
' > /app/install_blender.sh && chmod +x /app/install_blender.sh

# Set environment variables for Blender
ENV BLENDER_PATH=/opt/blender/blender-2.93.13-linux-x64/blender

# Download spaCy English model
RUN python -m spacy download en_core_web_sm

# Pre-compile critical Python modules for faster startup
RUN python -m compileall /usr/local/lib/python3.9/site-packages/cv2
RUN python -m compileall /usr/local/lib/python3.9/site-packages/numpy

# Copy only the model preload script first
COPY preload_models.py ./
RUN chmod +x preload_models.py

# Copy optimized_ffmpeg.py 
COPY optimized_ffmpeg.py ./
RUN chmod +x optimized_ffmpeg.py

# Set environment variables to avoid downloads during runtime
ENV ULTRALYTICS_NO_DOWNLOAD=true
ENV EASYOCR_DOWNLOAD_ENABLED=False
# Set app model directories
ENV ULTRALYTICS_CACHE_DIR=/app/models
ENV EASYOCR_MODEL_DIR=/app/models

# Create minimal script to test model loading and initialize them properly
RUN echo 'import torch; print("PyTorch:", torch.__version__); print("CUDA Available:", torch.cuda.is_available()); print("Device count:", torch.cuda.device_count())' > /app/test_torch.py && \
    echo 'import sys; import os; from pathlib import Path; models_dir = Path("/app/models"); sys.path.append(str(models_dir))' > /app/test_models.py && \
    echo 'try:\n  from ultralytics import YOLO\n  model = YOLO("/app/models/yolov8n.pt")\n  print("Loaded YOLOv8n model:", model)\nexcept Exception as e:\n  print("Error loading YOLO model:", e)' >> /app/test_models.py && \
    echo 'try:\n  from ultralytics import YOLO\n  pose_model = YOLO("/app/models/yolov8n-pose.pt")\n  print("Loaded YOLOv8n-pose model:", pose_model)\nexcept Exception as e:\n  print("Error loading YOLOv8n-pose model:", e)' >> /app/test_models.py && \
    python /app/test_torch.py || echo "PyTorch test failed but continuing" && \
    python /app/test_models.py || echo "Model loading test failed but continuing"

# Preload all ML models during build time to avoid runtime delays
# Use || true to ensure build continues even if preloading fails
RUN ULTRALYTICS_NO_DOWNLOAD=false python preload_models.py || echo "Model preloading failed, continuing build regardless"

# Copy the rest of the application
COPY . .

# Create a volume for the models directory
VOLUME /app/models

# Set environment variables for performance
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV FLASK_APP=app.py
ENV FLASK_DEBUG=0
ENV CORS_ENABLED=true
ENV DISABLE_ML_MODELS=false
ENV LAZY_LOAD_MODELS=true
ENV OMP_NUM_THREADS=4
ENV OPENBLAS_NUM_THREADS=4
ENV MKL_NUM_THREADS=4
ENV VECLIB_MAXIMUM_THREADS=4
ENV NUMEXPR_NUM_THREADS=4

# Verify Blender installation
RUN /usr/local/bin/blender --version || echo "Blender verification failed, but continuing"

# Expose the port
EXPOSE 8080

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:${PORT}/health || exit 1

# Run the application with Gunicorn with increased timeout
CMD gunicorn --bind 0.0.0.0:$PORT \
    --workers 2 \
    --threads 8 \
    --timeout 600 \
    --graceful-timeout 300 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --worker-class gthread \
    --log-level info \
    app:app 