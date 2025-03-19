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
    pip install --no-cache-dir easyocr==1.6.2

# Install FFmpeg directly from default repositories
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libavcodec-extra \
    libavfilter-extra \
    && rm -rf /var/lib/apt/lists/*

# Create model directories and prefetch all required models
RUN mkdir -p /app/models/z-anatomy /app/models/z-anatomy/output /app/fallback_models

# Download YOLOv8 models with better error handling
RUN cd /app/models && \
    echo "Downloading YOLOv8 models..." && \
    wget -q -O yolov8n.pt https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt || echo "Failed to download yolov8n.pt but continuing" && \
    wget -q -O yolov8s.pt https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8s.pt || echo "Failed to download yolov8s.pt but continuing" && \
    wget -q -O yolov8n-pose.pt https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n-pose.pt || echo "Failed to download yolov8n-pose.pt but continuing" && \
    wget -q -O yolov8s-pose.pt https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8s-pose.pt || echo "Failed to download yolov8s-pose.pt but continuing"

# Try to download ONNX models (but these are optional)
RUN cd /app/models && \
    echo "Attempting to download ONNX models (optional)..." && \
    wget -q -O yolov8n.onnx https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.onnx || echo "Failed to download yolov8n.onnx but continuing" && \
    wget -q -O yolov8s.onnx https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8s.onnx || echo "Failed to download yolov8s.onnx but continuing" && \
    wget -q -O yolov8n-pose.onnx https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n-pose.onnx || echo "Failed to download yolov8n-pose.onnx but continuing" && \
    wget -q -O yolov8s-pose.onnx https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8s-pose.onnx || echo "Failed to download yolov8s-pose.onnx but continuing" && \
    echo "Model download attempts complete. Listing downloaded models:" && \
    ls -la /app/models/

# Directly download EasyOCR models during build
RUN cd /app/models && \
    echo "Downloading EasyOCR models..." && \
    wget -q -O craft_mlt_25k.pth https://github.com/JaidedAI/EasyOCR/releases/download/v1.3/craft_mlt_25k.pth || echo "Failed to download craft_mlt_25k.pth but continuing" && \
    wget -q -O english_g2.pth https://github.com/JaidedAI/EasyOCR/releases/download/v1.3/english_g2.pth || echo "Failed to download english_g2.pth but continuing" && \
    echo "EasyOCR model download attempts complete. Listing models:" && \
    ls -la /app/models/

# Install a specific portable version of Blender (2.93 LTS) which has better compatibility
RUN mkdir -p /opt/blender && \
    cd /opt/blender && \
    wget -q https://download.blender.org/release/Blender2.93/blender-2.93.13-linux-x64.tar.xz && \
    tar -xf blender-2.93.13-linux-x64.tar.xz && \
    rm blender-2.93.13-linux-x64.tar.xz && \
    ln -s /opt/blender/blender-2.93.13-linux-x64/blender /usr/local/bin/blender

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

# Set environment variables to prevent any runtime downloads
ENV ULTRALYTICS_CACHE_DIR=/app/models
ENV ULTRALYTICS_NO_DOWNLOAD=true
ENV EASYOCR_NO_RUNTIME_DOWNLOAD=true
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