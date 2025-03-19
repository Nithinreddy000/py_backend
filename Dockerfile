FROM ultralytics/ultralytics:latest

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
    && rm -rf /var/lib/apt/lists/*

# Create models directory structure
RUN mkdir -p /app/models/z-anatomy /app/models/z-anatomy/output /app/fallback_models

# Install Python dependencies with correct versions
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir numpy==1.24.3 && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir easyocr==1.6.2 && \
    echo "export EASYOCR_DOWNLOAD_ENABLED=False" >> /root/.bashrc && \
    pip install importlib_metadata setuptools

# Link Ultralytics models to our application models directory
RUN mkdir -p /app/models && \
    echo "Copying pre-installed YOLOv8 models to app directory..." && \
    # Find where the models are stored in the ultralytics installation
    ULTRALYTIC_MODEL_DIR=$(python -c "import ultralytics; from pathlib import Path; print(Path(ultralytics.__file__).parent / 'assets')") && \
    # Copy the models from ultralytics package to our app directory
    cp -v $ULTRALYTIC_MODEL_DIR/*.pt /app/models/ && \
    # Verify the models are copied
    ls -la /app/models/

# Download EasyOCR models directly from S3
RUN apt-get update && \
    apt-get install -y curl && \
    curl -L -o /app/models/craft_mlt_25k.pth https://easyocr.s3.us-east-2.amazonaws.com/craft_mlt_25k.pth && \
    curl -L -o /app/models/english_g2.pth https://easyocr.s3.us-east-2.amazonaws.com/english_g2.pth && \
    ls -la /app/models/ && \
    echo "craft_mlt_25k.pth size: $(stat -c %s /app/models/craft_mlt_25k.pth)" && \
    echo "english_g2.pth size: $(stat -c %s /app/models/english_g2.pth)" && \
    if [ ! -s /app/models/craft_mlt_25k.pth ] || [ ! -s /app/models/english_g2.pth ]; then \
      echo "ERROR: EasyOCR models failed to download. Build failed!" && \
      exit 1; \
    fi && \
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
RUN python -m compileall -q /usr/local/lib/python3*/site-packages/cv2
RUN python -m compileall -q /usr/local/lib/python3*/site-packages/numpy

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

# Create minimal script to test model loading
RUN echo 'import torch; print("PyTorch:", torch.__version__); print("CUDA Available:", torch.cuda.is_available()); print("Device count:", torch.cuda.device_count())' > /app/test_torch.py && \
    echo 'import os\nimport sys\nfrom pathlib import Path\nmodels_dir = Path("/app/models")\nsys.path.append(str(models_dir))' > /app/test_models.py && \
    echo 'try:\n  import ultralytics\n  print("Ultralytics version:", ultralytics.__version__)\n  print("YOLO models present:", ", ".join(str(p) for p in Path("/app/models").glob("*.pt")))\nexcept Exception as e:\n  print("Error importing ultralytics:", e)' >> /app/test_models.py && \
    echo 'try:\n  import cv2\n  print("OpenCV version:", cv2.__version__)\nexcept Exception as e:\n  print("Error importing OpenCV:", e)' >> /app/test_models.py && \
    python /app/test_torch.py && \
    python /app/test_models.py

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
RUN bash -c "/usr/local/bin/blender --version || echo 'Blender verification failed, but continuing'"

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