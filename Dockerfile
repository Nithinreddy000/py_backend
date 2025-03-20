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
    tesseract-ocr \
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
    pip install --no-cache-dir pytesseract

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

# Improved EasyOCR initialization - Create a script to initialize and cache models
RUN echo '#!/usr/bin/env python3\n\
import os\n\
import time\n\
import tempfile\n\
import numpy as np\n\
import cv2\n\
\n\
print("Initializing and caching EasyOCR model...")\n\
start_time = time.time()\n\
\n\
# Create a simple test image with numbers\n\
test_img = np.zeros((100, 200), dtype=np.uint8)\n\
cv2.putText(test_img, "123", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, 255, 2)\n\
test_img_path = os.path.join(tempfile.gettempdir(), "test_ocr.jpg")\n\
cv2.imwrite(test_img_path, test_img)\n\
\n\
# Initialize and verify EasyOCR\n\
import easyocr\n\
model_dir = "/root/.EasyOCR/model"\n\
print(f"Using model directory: {model_dir}")\n\
\n\
# Make sure the directory exists\n\
os.makedirs(model_dir, exist_ok=True)\n\
\n\
# Initialize reader with download_enabled\n\
print("Downloading and caching models...")\n\
reader = easyocr.Reader([\'en\'], gpu=False, download_enabled=True, \n\
                        model_storage_directory=model_dir, \n\
                        user_network_directory=model_dir, \n\
                        recog_network="english_g2")\n\
\n\
# Test OCR on sample image to ensure everything is loaded\n\
print("Testing OCR on sample image...")\n\
results = reader.readtext(test_img_path)\n\
print(f"OCR results: {results}")\n\
\n\
# List all downloaded models to verify\n\
print("Cached model files:")\n\
for root, dirs, files in os.walk(model_dir):\n\
    for file in files:\n\
        print(f" - {os.path.join(root, file)}")\n\
\n\
print(f"EasyOCR initialization completed in {time.time() - start_time:.2f} seconds")\n\
' > /tmp/init_easyocr.py && chmod +x /tmp/init_easyocr.py

# Run the initialization script to download and cache models
RUN python /tmp/init_easyocr.py

# Create an alternative PaddleOCR initialization script as a backup OCR option
RUN pip install --no-cache-dir paddleocr>=2.6.0
RUN echo '#!/usr/bin/env python3\n\
import os\n\
import time\n\
import tempfile\n\
import numpy as np\n\
import cv2\n\
\n\
print("Initializing and caching PaddleOCR model as backup...")\n\
start_time = time.time()\n\
\n\
# Create a simple test image with numbers\n\
test_img = np.zeros((100, 200), dtype=np.uint8)\n\
cv2.putText(test_img, "123", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, 255, 2)\n\
test_img_path = os.path.join(tempfile.gettempdir(), "test_ocr_paddle.jpg")\n\
cv2.imwrite(test_img_path, test_img)\n\
\n\
# Initialize and verify PaddleOCR\n\
from paddleocr import PaddleOCR\n\
ocr_model_dir = "/root/.paddleocr"\n\
print(f"Using model directory: {ocr_model_dir}")\n\
\n\
# Make sure the directory exists\n\
os.makedirs(ocr_model_dir, exist_ok=True)\n\
\n\
# Initialize PaddleOCR\n\
print("Downloading and caching PaddleOCR models...")\n\
ocr = PaddleOCR(use_angle_cls=True, lang="en", use_gpu=False, \n\
                show_log=True, use_space_char=True)\n\
\n\
# Test OCR on sample image to ensure everything is loaded\n\
print("Testing PaddleOCR on sample image...")\n\
results = ocr.ocr(test_img_path, cls=True)\n\
print(f"OCR results: {results}")\n\
\n\
print(f"PaddleOCR initialization completed in {time.time() - start_time:.2f} seconds")\n\
' > /tmp/init_paddleocr.py && chmod +x /tmp/init_paddleocr.py

# Run the PaddleOCR initialization script
RUN python /tmp/init_paddleocr.py

# Create a wrapper script that combines all OCR strategies
RUN echo '#!/usr/bin/env python3\n\
import numpy as np\n\
import os\n\
import sys\n\
\n\
# Create OCR wrapper class that tries multiple OCR systems\n\
class MultiOCR:\n\
    def __init__(self, use_gpu=False):\n\
        self.readers = []\n\
        self.reader_names = []\n\
        \n\
        # Try to initialize EasyOCR\n\
        try:\n\
            import easyocr\n\
            model_dir = "/root/.EasyOCR/model"\n\
            print("Initializing EasyOCR...")\n\
            easy_reader = easyocr.Reader([\'en\'], gpu=use_gpu, \n\
                            model_storage_directory=model_dir, \n\
                            download_enabled=False,  # Don\'t download again\n\
                            user_network_directory=model_dir, \n\
                            recog_network="english_g2")\n\
            \n\
            # Define wrapper to standardize output format\n\
            def easy_wrapper(image, **kwargs):\n\
                return easy_reader.readtext(image, **kwargs)\n\
                \n\
            self.readers.append(easy_wrapper)\n\
            self.reader_names.append("EasyOCR")\n\
            print("EasyOCR initialized successfully")\n\
        except Exception as e:\n\
            print(f"Error initializing EasyOCR: {e}")\n\
        \n\
        # Try to initialize PaddleOCR\n\
        try:\n\
            from paddleocr import PaddleOCR\n\
            print("Initializing PaddleOCR...")\n\
            paddle_reader = PaddleOCR(use_angle_cls=True, lang=\'en\', use_gpu=use_gpu)\n\
            \n\
            # Define wrapper to standardize output format\n\
            def paddle_wrapper(image, **kwargs):\n\
                results = paddle_reader.ocr(image, cls=True)\n\
                # Convert PaddleOCR format to EasyOCR format\n\
                standardized = []\n\
                if results and len(results) > 0 and results[0]:\n\
                    for line in results[0]:\n\
                        if len(line) == 2:  # bbox, (text, confidence)\n\
                            bbox, (text, conf) = line\n\
                            # PaddleOCR returns 4 points, EasyOCR wants 4 points too\n\
                            standardized.append([bbox, text, conf])\n\
                return standardized\n\
                \n\
            self.readers.append(paddle_wrapper)\n\
            self.reader_names.append("PaddleOCR")\n\
            print("PaddleOCR initialized successfully")\n\
        except Exception as e:\n\
            print(f"Error initializing PaddleOCR: {e}")\n\
        \n\
        # Add a fallback OCR using OpenCV + Tesseract if available\n\
        try:\n\
            import pytesseract\n\
            import cv2\n\
            \n\
            def tesseract_wrapper(image, **kwargs):\n\
                # Convert to grayscale if needed\n\
                if len(image.shape) == 3:\n\
                    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)\n\
                else:\n\
                    gray = image\n\
                    \n\
                # Apply threshold to get binary image\n\
                thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]\n\
                \n\
                # Perform OCR\n\
                data = pytesseract.image_to_data(thresh, output_type=pytesseract.Output.DICT)\n\
                \n\
                # Convert to EasyOCR format\n\
                results = []\n\
                for i in range(len(data["text"])):\n\
                    if data["text"][i].strip():\n\
                        x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]\n\
                        # Create bbox in format [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]\n\
                        bbox = [[x, y], [x+w, y], [x+w, y+h], [x, y+h]]\n\
                        conf = float(data["conf"][i]) / 100.0\n\
                        results.append([bbox, data["text"][i], conf])\n\
                return results\n\
                \n\
            self.readers.append(tesseract_wrapper)\n\
            self.reader_names.append("Tesseract")\n\
            print("Tesseract OCR initialized successfully")\n\
        except Exception as e:\n\
            print(f"Tesseract not available: {e}")\n\
        \n\
        # Always add a dummy reader as final fallback\n\
        def dummy_wrapper(image, **kwargs):\n\
            return []\n\
            \n\
        self.readers.append(dummy_wrapper)\n\
        self.reader_names.append("Dummy")\n\
        \n\
        print(f"MultiOCR initialized with {len(self.readers)} readers: {self.reader_names}")\n\
    \n\
    def readtext(self, image, **kwargs):\n\
        """Try all readers in sequence until one works."""\n\
        for i, (reader, name) in enumerate(zip(self.readers, self.reader_names)):\n\
            try:\n\
                results = reader(image, **kwargs)\n\
                if results:  # Only return if we got actual results\n\
                    print(f"Using {name} OCR results: {len(results)} items found")\n\
                    return results\n\
            except Exception as e:\n\
                print(f"Error with {name} OCR: {e}")\n\
                # Continue to next reader\n\
        \n\
        # If all readers failed, return empty list\n\
        return []\n\
\n\
# Test the MultiOCR class\n\
if __name__ == "__main__":\n\
    import cv2\n\
    import time\n\
    import tempfile\n\
    \n\
    # Create a test image\n\
    test_img = np.zeros((100, 200), dtype=np.uint8)\n\
    cv2.putText(test_img, "123", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, 255, 2)\n\
    test_path = os.path.join(tempfile.gettempdir(), "multiocr_test.jpg")\n\
    cv2.imwrite(test_path, test_img)\n\
    \n\
    # Initialize MultiOCR\n\
    ocr = MultiOCR(use_gpu=False)\n\
    \n\
    # Test it\n\
    start_time = time.time()\n\
    results = ocr.readtext(test_path)\n\
    elapsed = time.time() - start_time\n\
    \n\
    print(f"MultiOCR test results: {results}")\n\
    print(f"OCR completed in {elapsed:.2f} seconds")\n\
\n\
    # Save to module that can be imported\n\
    with open("/root/multiocr.py", "w") as f:\n\
        f.write(open(__file__).read())\n\
    print("MultiOCR module saved to /root/multiocr.py")\n\
' > /tmp/multiocr.py && chmod +x /tmp/multiocr.py

# Run the multi-OCR script to verify it works
RUN python /tmp/multiocr.py

# Copy the MultiOCR module to the Python path and application directory
RUN cp /root/multiocr.py /usr/local/lib/python3.9/site-packages/ && \
    cp /root/multiocr.py /app/multiocr.py

# Create a wrapper script to modify EasyOCR behavior
RUN echo '#!/usr/bin/env python3\n\
# Monkey patch EasyOCR to be faster\n\
import sys\n\
import os\n\
import time\n\
\n\
def patch_easyocr():\n\
    try:\n\
        import easyocr\n\
        original_init = easyocr.Reader.__init__\n\
        \n\
        # Override the initialization to use cached models\n\
        def faster_init(self, lang_list, gpu=True, model_storage_directory=None,\n\
                       download_enabled=True, user_network_directory=None, recog_network=None,\n\
                       detector_network=None, **kwargs):\n\
            # Set default paths to our cached models\n\
            if model_storage_directory is None:\n\
                model_storage_directory = "/root/.EasyOCR/model"\n\
            if user_network_directory is None:\n\
                user_network_directory = "/root/.EasyOCR/model"\n\
            if recog_network is None:\n\
                recog_network = "english_g2"  # Use smaller model\n\
                \n\
            # Call original but with download_enabled=False to use cached versions\n\
            original_init(self, lang_list, gpu=gpu,\n\
                          model_storage_directory=model_storage_directory,\n\
                          download_enabled=False,  # Always use cached\n\
                          user_network_directory=user_network_directory,\n\
                          recog_network=recog_network,\n\
                          detector_network=detector_network, **kwargs)\n\
        \n\
        # Apply the patch\n\
        easyocr.Reader.__init__ = faster_init\n\
        print("Applied EasyOCR initialization patch for faster loading")\n\
        \n\
        # Return True for success\n\
        return True\n\
    except Exception as e:\n\
        print(f"Error patching EasyOCR: {e}")\n\
        return False\n\
\n\
# Execute the patch\n\
success = patch_easyocr()\n\
print(f"EasyOCR patching {\'successful\' if success else \'failed\'}")\n\
\n\
# Store as a module\n\
with open("/usr/local/lib/python3.9/site-packages/easyocr_patch.py", "w") as f:\n\
    f.write(open(__file__).read())\n\
print("EasyOCR patch module saved")\n\
' > /tmp/patch_easyocr.py && chmod +x /tmp/patch_easyocr.py

# Execute the patch script
RUN python /tmp/patch_easyocr.py

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