#!/usr/bin/env python3

"""
Script to preload ML models during container build to speed up first-time video processing.
This eliminates the delay when models need to be downloaded during runtime.
"""

import os
import sys
import subprocess
import urllib.request
import shutil
from pathlib import Path

# Directory to store models
MODEL_DIR = Path("./models")
MODEL_DIR.mkdir(exist_ok=True)
print(f"Downloading models to {MODEL_DIR.absolute()}")

# URLs for common ML models used in video processing
MODEL_URLS = {
    # YOLOv8 models
    "yolov8n.pt": "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt",
    "yolov8s.pt": "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8s.pt",
    
    # ONNX runtime models
    "yolov8n.onnx": "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.onnx",
    
    # Pose estimation models
    "yolov8n-pose.pt": "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n-pose.pt",
    "yolov8s-pose.pt": "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8s-pose.pt",
    
    # OCR models for jersey detection
    "easyocr_detection.pth": "https://github.com/JaidedAI/EasyOCR/releases/download/v1.3/craft_mlt_25k.pth",
    "easyocr_recognition_en.pth": "https://github.com/JaidedAI/EasyOCR/releases/download/v1.3/english_g2.pth"
}

def download_file(url, destination):
    """Download a file from URL to destination with progress indication."""
    try:
        print(f"Downloading {url} to {destination}")
        
        # Create a simple progress display
        def report_progress(block_num, block_size, total_size):
            read_so_far = block_num * block_size
            if total_size > 0:
                percent = read_so_far * 100 / total_size
                progress = int(percent / 2)
                sys.stdout.write(f"\rProgress: |{'=' * progress}{' ' * (50-progress)}| {percent:.1f}% Complete")
                sys.stdout.flush()
            else:
                sys.stdout.write(f"\rDownloaded {read_so_far} bytes")
                sys.stdout.flush()
                
        # Actually download the file
        urllib.request.urlretrieve(url, destination, reporthook=report_progress)
        print(f"\nSuccessfully downloaded {url}")
        return True
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False

def preload_ultralytics_models():
    """Preload Ultralytics/YOLO models using Python API."""
    try:
        from ultralytics import YOLO
        
        # Models to preload
        models = ["yolov8n.pt", "yolov8s.pt", "yolov8n-pose.pt"]
        
        for model_name in models:
            print(f"Preloading {model_name} using Ultralytics API")
            model = YOLO(model_name)
            # Perform a test prediction to ensure the model is loaded
            test_img_path = "test_image.jpg"
            with open(test_img_path, "wb") as f:
                f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x03\x02\x02\x03\x02\x02\x03\x03\x03\x03\x04\x03\x03\x04\x05\x08\x05\x05\x04\x04\x05\n\x07\x07\x06\x08\x0c\n\x0c\x0c\x0b\n\x0b\x0b\r\x0e\x12\x10\r\x0e\x11\x0e\x0b\x0b\x10\x16\x10\x11\x13\x14\x15\x15\x15\x0c\x0f\x17\x18\x16\x14\x18\x12\x14\x15\x14\xff\xdb\x00C\x01\x03\x04\x04\x05\x04\x05\t\x05\x05\t\x14\r\x0b\r\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\xff\xc2\x00\x11\x08\x00\x01\x00\x01\x03\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\n\xff\xc4\x00\x14\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x10\x03\x10\x00\x00\x01\x95\x00\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x01\x05\x02\x00\xff\xc4\x00\x14\x11\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x03\x01\x01?\x01\x00\xff\xc4\x00\x14\x11\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x02\x01\x01?\x01\x00\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x06?\x02\x00\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x01?!\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x00\x03\x00\x00\x00\x10\x00\xff\xc4\x00\x14\x11\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x03\x01\x01?\x10\x00\xff\xc4\x00\x14\x11\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x02\x01\x01?\x10\x00\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x01?\x10\x00\xff\xd9')
            
            result = model(test_img_path)
            print(f"Successfully loaded and tested {model_name}")
            
        print("All Ultralytics models preloaded")
        return True
    except Exception as e:
        print(f"Error preloading Ultralytics models: {e}")
        return False

def preload_easyocr():
    """Preload EasyOCR model."""
    try:
        import easyocr
        
        print("Preloading EasyOCR models")
        reader = easyocr.Reader(['en'])
        print("Successfully loaded EasyOCR models")
        return True
    except Exception as e:
        print(f"Error preloading EasyOCR models: {e}")
        return False

def main():
    """Main function to download and preload all models."""
    print("Starting model preloading process...")
    
    # First, download models directly
    for model_name, url in MODEL_URLS.items():
        output_path = MODEL_DIR / model_name
        if output_path.exists():
            print(f"Model {model_name} already exists at {output_path}, skipping download")
        else:
            download_file(url, output_path)
    
    # Then, preload models using the Python API
    preload_ultralytics_models()
    preload_easyocr()
    
    print("Model preloading completed!")

if __name__ == "__main__":
    main() 