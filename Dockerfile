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
    pip install --no-cache-dir -r requirements.txt

# Download spaCy English model
RUN python -m spacy download en_core_web_sm

# Install specific version of ultralytics that works with pose models and easyocr
RUN pip install --no-cache-dir ultralytics==8.0.20 easyocr && \
    mkdir -p /root/.cache/torch/hub/ultralytics_yolov5_master && \
    mkdir -p /root/.cache/torch/hub/checkpoints && \
    mkdir -p /root/.config/easyocr && \
    mkdir -p /root/.EasyOCR/model

# Download YOLO models first without loading them
RUN wget -q https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt -O /root/.cache/torch/hub/checkpoints/yolov8n.pt && \
    wget -q https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8s.pt -O /root/.cache/torch/hub/checkpoints/yolov8s.pt && \
    wget -q https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n-pose.pt -O /root/.cache/torch/hub/checkpoints/yolov8n-pose.pt

# Deeper inspection of ultralytics module structure to find Pose model
RUN echo 'import inspect, pkgutil; import ultralytics; print("Available modules in ultralytics:", [name for _, name, _ in pkgutil.iter_modules(ultralytics.__path__)]); import ultralytics.yolo; print("Modules in ultralytics.yolo:", [name for _, name, _ in pkgutil.iter_modules(ultralytics.yolo.__path__)]); import importlib; try: module = importlib.import_module("ultralytics.yolo.v8.pose"); print("Found pose module in ultralytics.yolo.v8.pose"); print("Contents:", dir(module)); except ImportError: print("No module ultralytics.yolo.v8.pose"); try: from ultralytics import YOLO; model = YOLO("yolov8n-pose.pt"); print("Model type:", type(model)); print("Model dir:", dir(model)); except Exception as e: print("Error loading model:", e)' > /tmp/deep_inspect.py && \
    python /tmp/deep_inspect.py

# Create the monkey patch based on inspection results
RUN mkdir -p /tmp/patch && \
    echo 'import sys' > /tmp/patch/patch.py && \
    echo 'from ultralytics import YOLO' >> /tmp/patch/patch.py && \
    echo 'temp_model = YOLO("yolov8n-pose.pt")' >> /tmp/patch/patch.py && \
    echo 'import ultralytics.nn.tasks' >> /tmp/patch/patch.py && \
    echo 'sys.modules["ultralytics.nn.tasks"].PoseModel = type(temp_model)' >> /tmp/patch/patch.py && \
    cat /tmp/patch/patch.py

# Apply the patch
RUN python -c "import sys; sys.path.append('/tmp/patch'); import patch; print('Monkey patch applied successfully')"

# Now load the models after the patch is applied
RUN python -c "from ultralytics import YOLO; print('Loading detection models...'); YOLO('yolov8n.pt'); YOLO('yolov8s.pt'); print('Loading pose model...'); pose_model = YOLO('yolov8n-pose.pt'); print('All models loaded successfully'); print('Pose model type:', type(pose_model))"

# Download EasyOCR models during build time (English model)
RUN python -c "import easyocr; reader = easyocr.Reader(['en'], gpu=False, download_enabled=True, model_storage_directory='/root/.EasyOCR/model')"

# Make the patch permanent by adding it to the Python path
RUN cp /tmp/patch/patch.py /usr/local/lib/python3.9/site-packages/ultralytics/nn/tasks_pose_patch.py && \
    echo "import ultralytics.nn.tasks_pose_patch" >> /usr/local/lib/python3.9/site-packages/ultralytics/nn/__init__.py

# Copy the rest of the application
COPY . .

# Create models directory if it doesn't exist
RUN mkdir -p models/z-anatomy models/z-anatomy/output

# Create fallback models directory
RUN mkdir -p fallback_models

# Create a volume for the models directory
VOLUME /app/models

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV FLASK_APP=app.py
ENV FLASK_DEBUG=0
ENV CORS_ENABLED=true
ENV DISABLE_ML_MODELS=false
ENV LAZY_LOAD_MODELS=false

# Verify Blender installation
RUN /usr/local/bin/blender --version

# Verify all models are available and the patch works
RUN python -c "from ultralytics import YOLO; print('Checking if all models work:'); YOLO('yolov8n.pt'); YOLO('yolov8s.pt'); YOLO('yolov8n-pose.pt'); print('All models verified successfully')"

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