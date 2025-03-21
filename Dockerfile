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
COPY <<-'EOT' /tmp/init_easyocr.py
#!/usr/bin/env python3
import os
import time
import tempfile
import numpy as np
import cv2

print("Initializing and caching EasyOCR model...")
start_time = time.time()

# Create a simple test image with numbers
test_img = np.zeros((100, 200), dtype=np.uint8)
cv2.putText(test_img, "123", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, 255, 2)
test_img_path = os.path.join(tempfile.gettempdir(), "test_ocr.jpg")
cv2.imwrite(test_img_path, test_img)

# Initialize and verify EasyOCR
import easyocr
model_dir = "/root/.EasyOCR/model"
print(f"Using model directory: {model_dir}")

# Make sure the directory exists
os.makedirs(model_dir, exist_ok=True)

# Initialize reader with download_enabled
print("Downloading and caching models...")
reader = easyocr.Reader(['en'], gpu=False, download_enabled=True, 
                        model_storage_directory=model_dir, 
                        user_network_directory=model_dir, 
                        recog_network="english_g2")

# Test OCR on sample image to ensure everything is loaded
print("Testing OCR on sample image...")
results = reader.readtext(test_img_path)
print(f"OCR results: {results}")

# List all downloaded models to verify
print("Cached model files:")
for root, dirs, files in os.walk(model_dir):
    for file in files:
        print(f" - {os.path.join(root, file)}")

print(f"EasyOCR initialization completed in {time.time() - start_time:.2f} seconds")
EOT

RUN chmod +x /tmp/init_easyocr.py

# Run the initialization script to download and cache models
RUN python /tmp/init_easyocr.py

# Create an alternative PaddleOCR initialization script as a backup OCR option
RUN pip install --no-cache-dir paddleocr>=2.6.0
COPY <<-'EOT' /tmp/init_paddleocr.py
#!/usr/bin/env python3
import os
import time
import tempfile
import numpy as np
import cv2

print("Initializing and caching PaddleOCR model as backup...")
start_time = time.time()

# Create a simple test image with numbers
test_img = np.zeros((100, 200), dtype=np.uint8)
cv2.putText(test_img, "123", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, 255, 2)
test_img_path = os.path.join(tempfile.gettempdir(), "test_ocr_paddle.jpg")
cv2.imwrite(test_img_path, test_img)

# Initialize and verify PaddleOCR
from paddleocr import PaddleOCR
ocr_model_dir = "/root/.paddleocr"
print(f"Using model directory: {ocr_model_dir}")

# Make sure the directory exists
os.makedirs(ocr_model_dir, exist_ok=True)

# Initialize PaddleOCR
print("Downloading and caching PaddleOCR models...")
ocr = PaddleOCR(use_angle_cls=True, lang="en", use_gpu=False, 
                show_log=True, use_space_char=True)

# Test OCR on sample image to ensure everything is loaded
print("Testing PaddleOCR on sample image...")
results = ocr.ocr(test_img_path, cls=True)
print(f"OCR results: {results}")

print(f"PaddleOCR initialization completed in {time.time() - start_time:.2f} seconds")
EOT

RUN chmod +x /tmp/init_paddleocr.py

# Run the PaddleOCR initialization script
RUN python /tmp/init_paddleocr.py

# Create a wrapper script that combines all OCR strategies
COPY <<-'EOT' /tmp/multiocr.py
#!/usr/bin/env python3
import numpy as np
import os
import sys

# Create OCR wrapper class that tries multiple OCR systems
class MultiOCR:
    def __init__(self, use_gpu=False):
        self.readers = []
        self.reader_names = []
        
        # Try to initialize EasyOCR
        try:
            import easyocr
            model_dir = "/root/.EasyOCR/model"
            print("Initializing EasyOCR...")
            easy_reader = easyocr.Reader(['en'], gpu=use_gpu, 
                            model_storage_directory=model_dir, 
                            download_enabled=False,  # Don't download again
                            user_network_directory=model_dir, 
                            recog_network="english_g2")
            
            # Define wrapper to standardize output format
            def easy_wrapper(image, **kwargs):
                return easy_reader.readtext(image, **kwargs)
                
            self.readers.append(easy_wrapper)
            self.reader_names.append("EasyOCR")
            print("EasyOCR initialized successfully")
        except Exception as e:
            print(f"Error initializing EasyOCR: {e}")
        
        # Try to initialize PaddleOCR
        try:
            from paddleocr import PaddleOCR
            print("Initializing PaddleOCR...")
            paddle_reader = PaddleOCR(use_angle_cls=True, lang='en', use_gpu=use_gpu)
            
            # Define wrapper to standardize output format
            def paddle_wrapper(image, **kwargs):
                results = paddle_reader.ocr(image, cls=True)
                # Convert PaddleOCR format to EasyOCR format
                standardized = []
                if results and len(results) > 0 and results[0]:
                    for line in results[0]:
                        if len(line) == 2:  # bbox, (text, confidence)
                            bbox, (text, conf) = line
                            # PaddleOCR returns 4 points, EasyOCR wants 4 points too
                            standardized.append([bbox, text, conf])
                return standardized
                
            self.readers.append(paddle_wrapper)
            self.reader_names.append("PaddleOCR")
            print("PaddleOCR initialized successfully")
        except Exception as e:
            print(f"Error initializing PaddleOCR: {e}")
        
        # Add a fallback OCR using OpenCV + Tesseract if available
        try:
            import pytesseract
            import cv2
            
            def tesseract_wrapper(image, **kwargs):
                # Convert to grayscale if needed
                if len(image.shape) == 3:
                    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                else:
                    gray = image
                    
                # Apply threshold to get binary image
                thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
                
                # Perform OCR
                data = pytesseract.image_to_data(thresh, output_type=pytesseract.Output.DICT)
                
                # Convert to EasyOCR format
                results = []
                for i in range(len(data["text"])):
                    if data["text"][i].strip():
                        x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
                        # Create bbox in format [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
                        bbox = [[x, y], [x+w, y], [x+w, y+h], [x, y+h]]
                        conf = float(data["conf"][i]) / 100.0
                        results.append([bbox, data["text"][i], conf])
                return results
                
            self.readers.append(tesseract_wrapper)
            self.reader_names.append("Tesseract")
            print("Tesseract OCR initialized successfully")
        except Exception as e:
            print(f"Tesseract not available: {e}")
        
        # Always add a dummy reader as final fallback
        def dummy_wrapper(image, **kwargs):
            return []
            
        self.readers.append(dummy_wrapper)
        self.reader_names.append("Dummy")
        
        print(f"MultiOCR initialized with {len(self.readers)} readers: {self.reader_names}")
    
    def readtext(self, image, **kwargs):
        """Try all readers in sequence until one works."""
        for i, (reader, name) in enumerate(zip(self.readers, self.reader_names)):
            try:
                results = reader(image, **kwargs)
                if results:  # Only return if we got actual results
                    print(f"Using {name} OCR results: {len(results)} items found")
                    return results
            except Exception as e:
                print(f"Error with {name} OCR: {e}")
                # Continue to next reader
        
        # If all readers failed, return empty list
        return []

# Test the MultiOCR class
if __name__ == "__main__":
    import cv2
    import time
    import tempfile
    
    # Create a test image
    test_img = np.zeros((100, 200), dtype=np.uint8)
    cv2.putText(test_img, "123", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, 255, 2)
    test_path = os.path.join(tempfile.gettempdir(), "multiocr_test.jpg")
    cv2.imwrite(test_path, test_img)
    
    # Initialize MultiOCR
    ocr = MultiOCR(use_gpu=False)
    
    # Test it
    start_time = time.time()
    results = ocr.readtext(test_path)
    elapsed = time.time() - start_time
    
    print(f"MultiOCR test results: {results}")
    print(f"OCR completed in {elapsed:.2f} seconds")

    # Save to module that can be imported
    with open("/root/multiocr.py", "w") as f:
        f.write(open(__file__).read())
    print("MultiOCR module saved to /root/multiocr.py")
EOT

RUN chmod +x /tmp/multiocr.py

# Run the multi-OCR script to verify it works
RUN python /tmp/multiocr.py

# Copy the MultiOCR module to the Python path and application directory
RUN cp /root/multiocr.py /usr/local/lib/python3.9/site-packages/ && \
    cp /root/multiocr.py /app/multiocr.py

# Create a wrapper script to modify EasyOCR behavior
COPY <<-'EOT' /tmp/patch_easyocr.py
#!/usr/bin/env python3
# Monkey patch EasyOCR to be faster
import sys
import os
import time

def patch_easyocr():
    try:
        import easyocr
        original_init = easyocr.Reader.__init__
        
        # Override the initialization to use cached models
        def faster_init(self, lang_list, gpu=True, model_storage_directory=None,
                       download_enabled=True, user_network_directory=None, recog_network=None,
                       detector_network=None, **kwargs):
            # Set default paths to our cached models
            if model_storage_directory is None:
                model_storage_directory = "/root/.EasyOCR/model"
            if user_network_directory is None:
                user_network_directory = "/root/.EasyOCR/model"
            if recog_network is None:
                recog_network = "english_g2"  # Use smaller model
                
            # Call original but with download_enabled=False to use cached versions
            original_init(self, lang_list, gpu=gpu,
                          model_storage_directory=model_storage_directory,
                          download_enabled=False,  # Always use cached
                          user_network_directory=user_network_directory,
                          recog_network=recog_network,
                          detector_network=detector_network, **kwargs)
        
        # Apply the patch
        easyocr.Reader.__init__ = faster_init
        print("Applied EasyOCR initialization patch for faster loading")
        
        # Return True for success
        return True
    except Exception as e:
        print(f"Error patching EasyOCR: {e}")
        return False

# Execute the patch
success = patch_easyocr()
print(f"EasyOCR patching {'successful' if success else 'failed'}")

# Store as a module
with open("/usr/local/lib/python3.9/site-packages/easyocr_patch.py", "w") as f:
    f.write(open(__file__).read())
print("EasyOCR patch module saved")
EOT

RUN chmod +x /tmp/patch_easyocr.py

# Execute the patch script
RUN python /tmp/patch_easyocr.py

# Create a wrapper script that modifies the module after it's fully loaded
COPY <<-'EOT' /tmp/patch_ultralytics.py
#!/usr/bin/env python3
# First, fully import and initialize ultralytics
import ultralytics
import sys
import types

# Verify the package is imported and ready
print("Ultralytics version:", ultralytics.__version__)
print("Available modules:", [name for name in dir(ultralytics) if not name.startswith("_")])

# Now that the module is fully loaded, we can create our PoseModel class
# Define a dummy PoseModel class that will be used as a placeholder
class PoseModel(object):
    def __init__(self, *args, **kwargs):
        from ultralytics import YOLO
        self.model = YOLO(*args, **kwargs)
        for attr in dir(self.model):
            if not attr.startswith("_"):
                setattr(self, attr, getattr(self.model, attr))

    def __call__(self, *args, **kwargs):
        return self.model(*args, **kwargs)

# Add PoseModel to the ultralytics.nn.tasks module
import ultralytics.nn.tasks
ultralytics.nn.tasks.PoseModel = PoseModel

print("PoseModel class successfully added to ultralytics.nn.tasks")

# Verify we can load the models
try:
    from ultralytics import YOLO
    detector = YOLO("yolov8n.pt")
    detector2 = YOLO("yolov8s.pt")
    pose_model = YOLO("yolov8n-pose.pt")
    print("Successfully loaded all models")
except Exception as e:
    print("Error loading models:", e)
EOT

RUN chmod +x /tmp/patch_ultralytics.py

# Apply the patch 
RUN python /tmp/patch_ultralytics.py

# Create a startup script that applies the patch at runtime
COPY <<-'EOT' /usr/local/lib/python3.9/site-packages/ultralytics_patch.py
#!/usr/bin/env python3
import sys
import types

def patch_ultralytics():
    import ultralytics.nn.tasks
    from ultralytics import YOLO
    
    if not hasattr(ultralytics.nn.tasks, "PoseModel"):
        # Define a wrapper class that delegates to YOLO
        class PoseModel(object):
            def __init__(self, *args, **kwargs):
                self.model = YOLO(*args, **kwargs)
                for attr in dir(self.model):
                    if not attr.startswith("_"):
                        setattr(self, attr, getattr(self.model, attr))
            
            def __call__(self, *args, **kwargs):
                return self.model(*args, **kwargs)
        
        # Add to the tasks module
        ultralytics.nn.tasks.PoseModel = PoseModel
        print("Applied PoseModel patch to ultralytics.nn.tasks")
    else:
        print("PoseModel already exists in ultralytics.nn.tasks")

# This will be imported when the app starts
patch_ultralytics()
EOT

# Add the patch to be imported at app startup
RUN echo "import ultralytics_patch" >> /usr/local/lib/python3.9/site-packages/ultralytics/__init__.py

# Create a test script to verify loading
COPY <<-'EOT' /tmp/test_models.py
#!/usr/bin/env python3
print("Testing YOLO model loading...")
try:
    from ultralytics import YOLO
    print("Successfully imported YOLO")
    # Test loading pose model
    model = YOLO("yolov8n-pose.pt")
    print("Successfully loaded pose model")
except Exception as e:
    print("Error:", e)
EOT

RUN chmod +x /tmp/test_models.py

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