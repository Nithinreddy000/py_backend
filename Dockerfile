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

# Install specific OpenCV build with optimizations pre-compiled
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir numpy==1.24.3 && \
    pip install --no-cache-dir opencv-contrib-python-headless==4.7.0.72 && \
    pip install --no-cache-dir -r requirements.txt

# Install FFmpeg directly from default repositories (avoid PPA that's causing errors)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libavcodec-extra \
    libavfilter-extra \
    && rm -rf /var/lib/apt/lists/*

# Download spaCy English model
RUN python -m spacy download en_core_web_sm

# Pre-compile critical Python modules for faster startup
RUN python -m compileall /usr/local/lib/python3.9/site-packages/cv2
RUN python -m compileall /usr/local/lib/python3.9/site-packages/numpy

# Copy the rest of the application
COPY . .

# Create models directory if it doesn't exist
RUN mkdir -p models/z-anatomy models/z-anatomy/output

# Create fallback models directory
RUN mkdir -p fallback_models

# Make the preload script executable
RUN chmod +x preload_models.py
RUN chmod +x optimized_ffmpeg.py

# Preload all ML models during build time to avoid runtime delays
RUN python preload_models.py

# Install more conservative set of video acceleration libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libva-drm2 \
    libva2 \
    && rm -rf /var/lib/apt/lists/*

# Test if GPU acceleration is available and optimize FFmpeg settings
RUN python -c "from optimized_ffmpeg import get_gpu_encoding_settings; print(f'Using GPU encoding settings: {get_gpu_encoding_settings()}')"

# Create a volume for the models directory
VOLUME /app/models

# Set environment variables for performance
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV FLASK_APP=app.py
ENV FLASK_DEBUG=0
ENV CORS_ENABLED=true
ENV DISABLE_ML_MODELS=false
ENV LAZY_LOAD_MODELS=false
ENV OMP_NUM_THREADS=4
ENV OPENBLAS_NUM_THREADS=4
ENV MKL_NUM_THREADS=4
ENV VECLIB_MAXIMUM_THREADS=4
ENV NUMEXPR_NUM_THREADS=4

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