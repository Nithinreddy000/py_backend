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

# Install a known working version of ultralytics
RUN pip install --no-cache-dir "ultralytics==8.0.145" easyocr && \
    mkdir -p /root/.cache/torch/hub/ultralytics_yolov5_master && \
    mkdir -p /root/.cache/torch/hub/checkpoints && \
    mkdir -p /root/.config/easyocr && \
    mkdir -p /root/.EasyOCR/model

# Download YOLO models first without loading them
RUN wget -q https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt -O /root/.cache/torch/hub/checkpoints/yolov8n.pt && \
    wget -q https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8s.pt -O /root/.cache/torch/hub/checkpoints/yolov8s.pt && \
    wget -q https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n-pose.pt -O /root/.cache/torch/hub/checkpoints/yolov8n-pose.pt

# Create a wrapper script that modifies the module after it's fully loaded
RUN echo '#!/usr/bin/env python3\n\
# First, fully import and initialize ultralytics\n\
import ultralytics\n\
import sys\n\
import types\n\
\n\
# Verify the package is imported and ready\n\
print("Ultralytics version:", ultralytics.__version__)\n\
print("Available modules:", [name for name in dir(ultralytics) if not name.startswith("_")])\n\
\n\
# Now that the module is fully loaded, we can create our PoseModel class\n\
# Define a dummy PoseModel class that will be used as a placeholder\n\
class PoseModel(object):\n\
    def __init__(self, *args, **kwargs):\n\
        from ultralytics import YOLO\n\
        self.model = YOLO(*args, **kwargs)\n\
        for attr in dir(self.model):\n\
            if not attr.startswith("_"):\n\
                setattr(self, attr, getattr(self.model, attr))\n\
\n\
    def __call__(self, *args, **kwargs):\n\
        return self.model(*args, **kwargs)\n\
\n\
# Add PoseModel to the ultralytics.nn.tasks module\n\
import ultralytics.nn.tasks\n\
ultralytics.nn.tasks.PoseModel = PoseModel\n\
\n\
print("PoseModel class successfully added to ultralytics.nn.tasks")\n\
\n\
# Verify we can load the models\n\
try:\n\
    from ultralytics import YOLO\n\
    detector = YOLO("yolov8n.pt")\n\
    detector2 = YOLO("yolov8s.pt")\n\
    pose_model = YOLO("yolov8n-pose.pt")\n\
    print("Successfully loaded all models")\n\
except Exception as e:\n\
    print("Error loading models:", e)\n\
' > /tmp/patch_ultralytics.py && chmod +x /tmp/patch_ultralytics.py

# Apply the patch 
RUN python /tmp/patch_ultralytics.py

# Create a startup script that applies the patch at runtime
RUN echo '#!/usr/bin/env python3\n\
import sys\n\
import types\n\
\n\
def patch_ultralytics():\n\
    import ultralytics.nn.tasks\n\
    from ultralytics import YOLO\n\
    \n\
    if not hasattr(ultralytics.nn.tasks, "PoseModel"):\n\
        # Define a wrapper class that delegates to YOLO\n\
        class PoseModel(object):\n\
            def __init__(self, *args, **kwargs):\n\
                self.model = YOLO(*args, **kwargs)\n\
                for attr in dir(self.model):\n\
                    if not attr.startswith("_"):\n\
                        setattr(self, attr, getattr(self.model, attr))\n\
            \n\
            def __call__(self, *args, **kwargs):\n\
                return self.model(*args, **kwargs)\n\
        \n\
        # Add to the tasks module\n\
        ultralytics.nn.tasks.PoseModel = PoseModel\n\
        print("Applied PoseModel patch to ultralytics.nn.tasks")\n\
    else:\n\
        print("PoseModel already exists in ultralytics.nn.tasks")\n\
\n\
# This will be imported when the app starts\n\
patch_ultralytics()\n\
' > /usr/local/lib/python3.9/site-packages/ultralytics_patch.py

# Add the patch to be imported at app startup
RUN echo "import ultralytics_patch" >> /usr/local/lib/python3.9/site-packages/ultralytics/__init__.py

# Create a test script to verify loading
RUN echo '#!/usr/bin/env python3\n\
print("Testing YOLO model loading...")\n\
try:\n\
    from ultralytics import YOLO\n\
    print("Successfully imported YOLO")\n\
    # Test loading pose model\n\
    model = YOLO("yolov8n-pose.pt")\n\
    print("Successfully loaded pose model")\n\
except Exception as e:\n\
    print("Error:", e)\n\
' > /tmp/test_models.py && chmod +x /tmp/test_models.py

# Test the model loading works
RUN python /tmp/test_models.py

# Download EasyOCR models during build time (English model)
RUN python -c "import easyocr; reader = easyocr.Reader(['en'], gpu=False, download_enabled=True, model_storage_directory='/root/.EasyOCR/model')"

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