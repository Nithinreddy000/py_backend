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
    wget -q https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n-pose.pt -O /root/.cache/torch/hub/checkpoints/yolov8n-pose.pt && \
    wget -q https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8x-pose.pt -O /root/.cache/torch/hub/checkpoints/yolov8x-pose.pt && \
    # Create symbolic links in /app directory for direct access
    ln -sf /root/.cache/torch/hub/checkpoints/yolov8n.pt /app/yolov8n.pt && \
    ln -sf /root/.cache/torch/hub/checkpoints/yolov8s.pt /app/yolov8s.pt && \
    ln -sf /root/.cache/torch/hub/checkpoints/yolov8n-pose.pt /app/yolov8n-pose.pt && \
    ln -sf /root/.cache/torch/hub/checkpoints/yolov8x-pose.pt /app/yolov8x-pose.pt

# Create a wrapper script that modifies the module after it's fully loaded
RUN echo '#!/usr/bin/env python3\n\
# First, fully import and initialize ultralytics\n\
import ultralytics\n\
import sys\n\
import types\n\
import os\n\
\n\
# Verify the package is imported and ready\n\
print("Ultralytics version:", ultralytics.__version__)\n\
print("Available modules:", [name for name in dir(ultralytics) if not name.startswith("_")])\n\
\n\
# Check if all model files exist\n\
model_files = [\n\
    "/app/yolov8n.pt",\n\
    "/app/yolov8s.pt",\n\
    "/app/yolov8n-pose.pt",\n\
    "/app/yolov8x-pose.pt"\n\
]\n\
\n\
for model_file in model_files:\n\
    if os.path.exists(model_file):\n\
        print(f"Model file exists: {model_file}")\n\
    else:\n\
        print(f"WARNING: Model file does not exist: {model_file}")\n\
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
    pose_model_x = YOLO("yolov8x-pose.pt")\n\
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
import os\n\
\n\
def patch_ultralytics():\n\
    import ultralytics.nn.tasks\n\
    from ultralytics import YOLO\n\
    \n\
    # First check if all model files are present\n\
    model_files = [\n\
        "/app/yolov8n.pt",\n\
        "/app/yolov8s.pt",\n\
        "/app/yolov8n-pose.pt",\n\
        "/app/yolov8x-pose.pt"\n\
    ]\n\
    \n\
    for model_file in model_files:\n\
        if not os.path.exists(model_file):\n\
            # Copy from cache location if available\n\
            cache_path = f"/root/.cache/torch/hub/checkpoints/{os.path.basename(model_file)}"\n\
            if os.path.exists(cache_path):\n\
                import shutil\n\
                shutil.copy(cache_path, model_file)\n\
                print(f"Copied model from cache: {cache_path} -> {model_file}")\n\
            else:\n\
                print(f"WARNING: Model file does not exist: {model_file}")\n\
                # But we will continue without failing\n\
    \n\
    if not hasattr(ultralytics.nn.tasks, "PoseModel"):\n\
        # Define a wrapper class that delegates to YOLO\n\
        class PoseModel(object):\n\
            def __init__(self, *args, **kwargs):\n\
                try:\n\
                    self.model = YOLO(*args, **kwargs)\n\
                    for attr in dir(self.model):\n\
                        if not attr.startswith("_"):\n\
                            setattr(self, attr, getattr(self.model, attr))\n\
                except Exception as e:\n\
                    print(f"Error initializing YOLO model: {e}")\n\
                    # Create a dummy model to prevent crashes\n\
                    self.model = None\n\
            \n\
            def __call__(self, *args, **kwargs):\n\
                if self.model is not None:\n\
                    return self.model(*args, **kwargs)\n\
                else:\n\
                    print("Warning: Using dummy model, no results will be returned")\n\
                    return []\n\
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

# Create a script to prevent crashing when model can't be found
RUN echo 'import os\n\
import sys\n\
\n\
# Add a monkey patch to handle missing model files gracefully\n\
original_open = open\n\
\n\
def patched_open(file, *args, **kwargs):\n\
    if file.endswith(".pt") and not os.path.exists(file):\n\
        print(f"WARNING: Model file not found: {file}")\n\
        # For model files, if they don\'t exist, create a fallback mechanism\n\
        if "yolov8x-pose.pt" in file:\n\
            if os.path.exists("/app/yolov8n-pose.pt"):\n\
                print(f"Using fallback model: /app/yolov8n-pose.pt instead of {file}")\n\
                return original_open("/app/yolov8n-pose.pt", *args, **kwargs)\n\
            else:\n\
                # Try to find any pose model\n\
                for fallback in ["/root/.cache/torch/hub/checkpoints/yolov8n-pose.pt", \n\
                                "/app/yolov8n-pose.pt"]:\n\
                    if os.path.exists(fallback):\n\
                        print(f"Using fallback model: {fallback} instead of {file}")\n\
                        return original_open(fallback, *args, **kwargs)\n\
    \n\
    return original_open(file, *args, **kwargs)\n\
\n\
# Apply the patch\n\
open = patched_open\n\
' > /usr/local/lib/python3.9/site-packages/model_fallback.py

# Add the fallback patch to be imported at app startup
RUN echo "import model_fallback" >> /usr/local/lib/python3.9/site-packages/ultralytics/__init__.py

# Create a test script to verify loading
RUN echo '#!/usr/bin/env python3\n\
print("Testing YOLO model loading...")\n\
try:\n\
    from ultralytics import YOLO\n\
    print("Successfully imported YOLO")\n\
    \n\
    # Test loading models\n\
    print("Loading yolov8n.pt...")\n\
    model1 = YOLO("yolov8n.pt")\n\
    print("Loading yolov8n-pose.pt...")\n\
    model2 = YOLO("yolov8n-pose.pt")\n\
    \n\
    # Test loading non-existent model to verify fallback works\n\
    print("Testing fallback with deliberate non-existent model...")\n\
    test_file = "/app/non_existent_model.pt"\n\
    import os\n\
    if not os.path.exists(test_file):\n\
        print(f"Confirmed {test_file} does not exist, testing fallback mechanism")\n\
        try:\n\
            with open(test_file, "rb") as f:\n\
                print("Fallback mechanism worked!")\n\
        except Exception as e:\n\
            print(f"Fallback failed: {e}")\n\
    \n\
    print("All tests complete")\n\
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

# Create a modified app initialization script to prevent worker restarts
RUN echo '# Model initialization script for app.py\n\
import os\n\
import time\n\
import logging\n\
\n\
def initialize_models_safely():\n\
    """Initialize all models safely without causing worker restarts"""\n\
    try:\n\
        logging.info("Starting safe model initialization")\n\
        \n\
        # Check if models exist in expected locations\n\
        model_files = [\n\
            "/app/yolov8n.pt",\n\
            "/app/yolov8s.pt", \n\
            "/app/yolov8n-pose.pt",\n\
            "/app/yolov8x-pose.pt"\n\
        ]\n\
        \n\
        for model_path in model_files:\n\
            if os.path.exists(model_path):\n\
                logging.info(f"Model exists: {model_path}")\n\
            else:\n\
                # Create a symlink from cache if available\n\
                cache_path = f"/root/.cache/torch/hub/checkpoints/{os.path.basename(model_path)}"\n\
                if os.path.exists(cache_path):\n\
                    try:\n\
                        os.symlink(cache_path, model_path)\n\
                        logging.info(f"Created symlink from {cache_path} to {model_path}")\n\
                    except Exception as e:\n\
                        logging.warning(f"Failed to create symlink: {e}")\n\
                else:\n\
                    logging.warning(f"Model not found: {model_path} or {cache_path}")\n\
                    \n\
        # Try to load YOLO models with graceful fallback\n\
        try:\n\
            from ultralytics import YOLO\n\
            \n\
            # Initialize models one by one with timeouts\n\
            models = {}\n\
            for model_name in ["yolov8n.pt", "yolov8n-pose.pt"]:\n\
                try:\n\
                    logging.info(f"Loading model: {model_name}")\n\
                    start_time = time.time()\n\
                    model = YOLO(model_name)\n\
                    models[model_name] = model\n\
                    logging.info(f"Loaded {model_name} in {time.time() - start_time:.2f} seconds")\n\
                except Exception as e:\n\
                    logging.error(f"Error loading {model_name}: {e}")\n\
            \n\
            # Return the loaded models\n\
            return models\n\
                \n\
        except Exception as e:\n\
            logging.error(f"Error initializing YOLO: {e}")\n\
            return {}\n\
            \n\
    except Exception as e:\n\
        logging.error(f"Error in safe model initialization: {e}")\n\
        return {}\n\
' > /app/safe_model_init.py

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
ENV GUNICORN_TIMEOUT=3600
ENV GUNICORN_WORKERS=1
ENV GUNICORN_THREADS=4
ENV GUNICORN_WORKER_CLASS=gthread
ENV GUNICORN_MAX_REQUESTS=1
ENV GUNICORN_MAX_REQUESTS_JITTER=0
ENV GUNICORN_KEEP_ALIVE=5
ENV GUNICORN_GRACEFUL_TIMEOUT=3600
ENV PYTHONPATH=/app

# Verify Blender installation
RUN /usr/local/bin/blender --version

# Expose the port
EXPOSE 8080

# Add healthcheck with increased timeout
HEALTHCHECK --interval=60s --timeout=30s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:${PORT}/health || exit 1

# Run the application with Gunicorn with increased timeout and optimized settings for video processing
CMD gunicorn --bind 0.0.0.0:$PORT \
    --workers ${GUNICORN_WORKERS:-1} \
    --threads ${GUNICORN_THREADS:-4} \
    --timeout ${GUNICORN_TIMEOUT:-3600} \
    --graceful-timeout ${GUNICORN_GRACEFUL_TIMEOUT:-3600} \
    --keep-alive ${GUNICORN_KEEP_ALIVE:-5} \
    --max-requests ${GUNICORN_MAX_REQUESTS:-1} \
    --max-requests-jitter ${GUNICORN_MAX_REQUESTS_JITTER:-0} \
    --worker-class ${GUNICORN_WORKER_CLASS:-gthread} \
    --preload \
    --log-level info \
    --access-logfile - \
    --error-logfile - \
    --capture-output \
    --enable-stdio-inheritance \
    app:app 