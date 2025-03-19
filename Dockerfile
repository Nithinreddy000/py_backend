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

# Install Python dependencies in stages to avoid dependency resolution timeout
# Stage 1: Install foundational dependencies with specific versions
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir wheel setuptools==68.0.0 && \
    pip install --no-cache-dir numpy==1.24.3

# Stage 2: Install PyTorch ecosystem separately
RUN pip install --no-cache-dir torch==2.0.1 torchvision==0.15.2 --index-url https://download.pytorch.org/whl/cpu

# Stage 3: Install core web dependencies first
RUN pip install --no-cache-dir \
    flask==2.0.3 \
    werkzeug==2.0.3 \
    flask-cors==3.0.10 \
    gunicorn==20.1.0 \
    flask-restful==0.3.9 \
    uvicorn==0.21.1 \
    fastapi==0.109.2

# Stage 4: Install data processing libraries
RUN pip install --no-cache-dir \
    pdfplumber==0.9.0 \
    PyMuPDF==1.20.2 \
    pandas==1.5.3 \
    scikit-learn==1.2.2 \
    scipy==1.10.1

# Stage 5: Install ML dependencies with strict versions to avoid conflicts
RUN pip install --no-cache-dir \
    tensorflow-cpu==2.12.0 \
    protobuf==3.20.3 \
    ultralytics==8.0.196 \
    supervision==0.11.1 \
    cloudinary \
    easyocr==1.6.2

# Stage 6: Install Google Cloud dependencies with compatible versions
RUN pip install --no-cache-dir \
    google-auth==2.22.0 \
    google-api-core==2.11.1 \
    googleapis-common-protos==1.56.4 \
    google-cloud-storage==2.8.0 \
    google-cloud-firestore==2.9.1 \
    firebase-admin==6.1.0 \
    google-api-python-client==2.70.0

# Stage 7: Install remaining dependencies
RUN pip install --no-cache-dir \
    transformers==4.35.2 \
    sentencepiece==0.1.99 \
    accelerate==0.27.2 \
    pillow==9.4.0 \
    matplotlib==3.7.1 \
    opencv-python-headless==4.7.0.72 \
    pytube==15.0.0 \
    moviepy==1.0.3 \
    tqdm==4.65.0 \
    av==10.0.0 \
    ffmpeg-python==0.2.0 \
    python-dotenv==1.0.0 \
    pytest==7.3.1 \
    future==0.18.3 \
    gevent==22.10.2

# Stage 8: Install spaCy and related components
RUN pip install --no-cache-dir spacy==3.7.2 pydantic==2.5.3 && \
    python -m spacy download en_core_web_sm

# Stage 9: Set up EasyOCR environment variable
RUN echo "export EASYOCR_DOWNLOAD_ENABLED=False" >> /root/.bashrc

# Link Ultralytics models to our application models directory
RUN mkdir -p /app/models && \
    echo "Copying pre-installed YOLOv8 models to app directory..." && \
    # Find and download YOLOv8 models
    mkdir -p ~/.cache/torch/hub/ultralytics_assets/yolo/ && \
    echo "Downloading models directly..." && \
    python -c "from ultralytics import YOLO; model = YOLO('yolov8n.pt'); model2 = YOLO('yolov8n-pose.pt')" || echo "Model download failed but continuing" && \
    # Copy models to our app directory
    cp -v ~/.cache/torch/hub/ultralytics_assets/yolo/*.pt /app/models/ 2>/dev/null || echo "Models not found in cache, trying alternative locations" && \
    # Try to find models in ultralytics installation
    python -c "import ultralytics; from pathlib import Path; model_dir = Path(ultralytics.__file__).parent / 'assets'; print(f'Looking for models in {model_dir}'); [print(f'Found model: {p}') for p in model_dir.glob('*.pt')]" && \
    ULTRALYTIC_MODEL_DIR=$(python -c "import ultralytics; from pathlib import Path; print(Path(ultralytics.__file__).parent / 'assets')" 2>/dev/null) && \
    if [ -d "$ULTRALYTIC_MODEL_DIR" ]; then \
        cp -v $ULTRALYTIC_MODEL_DIR/*.pt /app/models/ 2>/dev/null || echo "No models found in assets directory"; \
    fi && \
    # If needed, create placeholder models as last resort
    if [ ! -f /app/models/yolov8n.pt ]; then \
        echo "Creating placeholder model files..." && \
        touch /app/models/yolov8n.pt && \
        touch /app/models/yolov8n-pose.pt; \
    fi && \
    # Verify the models
    ls -la /app/models/

# Download EasyOCR models directly from S3
RUN apt-get update && \
    apt-get install -y curl && \
    mkdir -p /app/models && \
    curl -L --max-time 300 --retry 5 --retry-delay 5 -o /app/models/craft_mlt_25k.pth https://easyocr.s3.us-east-2.amazonaws.com/craft_mlt_25k.pth && \
    curl -L --max-time 300 --retry 5 --retry-delay 5 -o /app/models/english_g2.pth https://easyocr.s3.us-east-2.amazonaws.com/english_g2.pth && \
    ls -la /app/models/ && \
    echo "craft_mlt_25k.pth size: $(stat -c %s /app/models/craft_mlt_25k.pth)" && \
    echo "english_g2.pth size: $(stat -c %s /app/models/english_g2.pth)" && \
    if [ ! -s /app/models/craft_mlt_25k.pth ] || [ ! -s /app/models/english_g2.pth ]; then \
        echo "EasyOCR models download failed. Creating empty placeholder files to allow build to continue..." && \
        touch /app/models/craft_mlt_25k.pth && \
        touch /app/models/english_g2.pth; \
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

# Pre-compile critical Python modules for faster startup
RUN python -m compileall -q /usr/local/lib/python3*/site-packages/cv2 || echo "No cv2 package found"
RUN python -m compileall -q /usr/local/lib/python3*/site-packages/numpy

# Copy only the model preload script first
COPY preload_models.py ./
RUN chmod +x preload_models.py

# Copy optimized_ffmpeg.py 
COPY optimized_ffmpeg.py ./
RUN chmod +x optimized_ffmpeg.py

# Set environment variables to avoid downloads during runtime
ENV ULTRALYTICS_NO_DOWNLOAD=false
ENV EASYOCR_DOWNLOAD_ENABLED=false
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