FROM python:3.9-slim

WORKDIR /app

# Copy requirements file first for better caching
COPY requirements.txt .

# Install required system dependencies including OpenCV dependencies
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
    && rm -rf /var/lib/apt/lists/*

# Install a specific portable version of Blender (2.93 LTS) which has better compatibility
RUN mkdir -p /opt/blender && \
    cd /opt/blender && \
    wget -q https://download.blender.org/release/Blender2.93/blender-2.93.13-linux-x64.tar.xz && \
    tar -xf blender-2.93.13-linux-x64.tar.xz && \
    rm blender-2.93.13-linux-x64.tar.xz && \
    ln -s /opt/blender/blender-2.93.13-linux-x64/blender /usr/local/bin/blender

# Set environment variables for Blender
ENV BLENDER_PATH=/opt/blender/blender-2.93.13-linux-x64/blender

# Upgrade pip and install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir blinker==1.6.2

# Download spaCy English model
RUN python -m spacy download en_core_web_sm

# Create directories for models
RUN mkdir -p models/yolo models/z-anatomy models/z-anatomy/output fallback_models

# Install specific compatible version of ultralytics for pose models
RUN pip install --no-cache-dir ultralytics==8.0.196 --force-reinstall

# Pre-download YOLO models to avoid runtime downloads
RUN echo "Downloading YOLO pose model..." && \
    python -c "from ultralytics import YOLO; model = YOLO('yolov8n-pose.pt'); print(f'Successfully loaded {model}')" && \
    python -c "from ultralytics import YOLO; model = YOLO('yolov8n.pt'); print(f'Successfully loaded {model}')" && \
    mkdir -p /root/.config/ultralytics && \
    chmod -R 777 /root/.config/ultralytics

# Pre-download EasyOCR models to avoid runtime downloads
RUN echo "Downloading EasyOCR models..." && \
    python -c "import easyocr; reader = easyocr.Reader(['en'], model_storage_directory='/app/models/easyocr', download_enabled=True); print('EasyOCR models downloaded successfully')" && \
    mkdir -p /root/.EasyOCR && \
    chmod -R 777 /root/.EasyOCR

# Copy the rest of the application
COPY . .

# Create a volume for the models directory
VOLUME /app/models

# Set environment variables for optimizing TensorFlow and model loading
ENV TF_ENABLE_ONEDNN_OPTS=0
ENV TF_CPP_MIN_LOG_LEVEL=2
ENV TF_FORCE_GPU_ALLOW_GROWTH=true
ENV LAZY_LOAD_MODELS=false
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV FLASK_APP=app.py
ENV FLASK_DEBUG=0
ENV CORS_ENABLED=true
ENV DISABLE_ML_MODELS=false

# Point to pre-downloaded models
ENV EASYOCR_MODULE_PATH=/app/models/easyocr
ENV YOLO_MODEL_PATH=/root/.config/ultralytics/models

# Create cache directories for models
RUN mkdir -p /root/.cache/torch
RUN mkdir -p /root/.cache/pip

# Verify Blender installation
RUN /usr/local/bin/blender --version

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