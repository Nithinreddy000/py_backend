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

# Set environment variables to disable problematic TensorFlow features
ENV TF_ENABLE_ONEDNN_OPTS=0
ENV TF_CPP_MIN_LOG_LEVEL=3
ENV DISABLE_TENSOR_FLOAT_32_EXECUTION=1
ENV TF_DISABLE_MKL=1
ENV NO_BF16_INSTRUCTIONS=1
ENV CUDA_VISIBLE_DEVICES=-1
ENV PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
ENV PYTHONNOUSERSITE=1

# Upgrade pip and install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir blinker==1.6.2

# Install PyTorch first with specific versions for compatibility
RUN pip install --no-cache-dir torch==1.13.1 torchvision==0.14.1 --index-url https://download.pytorch.org/whl/cpu

# Install other dependencies with better compatibility
RUN pip install --no-cache-dir "tensorflow-cpu<2.12.0" "numpy<1.24.0" --force-reinstall && \
    pip install --no-cache-dir ultralytics==8.0.196 --no-deps && \
    pip install --no-cache-dir "pillow>=9.4.0" && \
    pip install --no-cache-dir "transformers<4.30.0" --no-deps && \
    pip install --no-cache-dir "tokenizers<0.14.0"

# Download spaCy English model
RUN python -m spacy download en_core_web_sm

# Create directories for models
RUN mkdir -p models/yolo models/z-anatomy models/z-anatomy/output fallback_models

# Copy the download_models.py script first to pre-download models
COPY download_models.py /app/

# Pre-download models using our custom script
RUN chmod +x /app/download_models.py && \
    python /app/download_models.py

# Copy the rest of the application
COPY . .

# Create a volume for the models directory
VOLUME /app/models

# Set more environment variables for optimizing TensorFlow and model loading
ENV TF_FORCE_GPU_ALLOW_GROWTH=true
ENV LAZY_LOAD_MODELS=false
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV FLASK_APP=app.py
ENV FLASK_DEBUG=0
ENV CORS_ENABLED=true
ENV DISABLE_TRANSFORMERS=true

# Create a file to disable TensorFlow in transformers
RUN echo "Disabling TensorFlow in transformers for stability" > /app/disable_tf.txt

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
    --workers 1 \
    --threads 8 \
    --timeout 600 \
    --graceful-timeout 300 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --worker-class gthread \
    --log-level info \
    app:app 