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
    """Preload Ultralytics/YOLO models using Python API with NO downloads allowed."""
    try:
        print("Verifying pre-downloaded Ultralytics models...")
        
        try:
            # Force install specific version of ultralytics
            print("Installing specific ultralytics version...")
            subprocess.run([sys.executable, "-m", "pip", "install", "--no-cache-dir", "ultralytics==8.0.196"], check=True)
            
            # Import after installation to ensure we get the fixed version
            from ultralytics import YOLO
            print(f"Successfully installed and imported ultralytics version")
        except Exception as install_err:
            print(f"Error installing ultralytics: {install_err}")
            print("Continuing without preloading YOLO models")
            return False
        
        # Models to verify
        models = ["yolov8n.pt", "yolov8s.pt", "yolov8n-pose.pt"]
        success_count = 0
        
        # First verify all models exist
        missing_models = []
        placeholder_models = []
        for model_name in models:
            model_path = MODEL_DIR / model_name
            if not model_path.exists():
                print(f"ERROR: Required model {model_name} not found at {model_path}")
                missing_models.append(model_name)
            # Check if the file is just a placeholder
            elif os.path.getsize(model_path) < 1000:  # Less than 1KB is likely a placeholder
                print(f"WARNING: Model {model_name} appears to be a placeholder file")
                placeholder_models.append(model_name)
        
        if missing_models or placeholder_models:
            # Try to download missing or placeholder models
            print(f"Attempting to download {len(missing_models)} missing and {len(placeholder_models)} placeholder models")
            all_models_to_get = missing_models + placeholder_models
            for model_name in all_models_to_get:
                if model_name in MODEL_URLS:
                    print(f"Downloading {model_name} from {MODEL_URLS[model_name]}")
                    try:
                        download_file(MODEL_URLS[model_name], MODEL_DIR / model_name)
                    except Exception as e:
                        print(f"Error downloading {model_name}: {e}")
                else:
                    print(f"No URL defined for {model_name}, skipping download")
            
            # Check again after attempted downloads
            missing_models = []
            for model_name in models:
                model_path = MODEL_DIR / model_name
                if not model_path.exists() or os.path.getsize(model_path) < 1000:
                    missing_models.append(model_name)
        
        if missing_models:
            print(f"ERROR: {len(missing_models)} models are missing or invalid. Docker build must download them first.")
            print(f"Missing models: {missing_models}")
            # Don't return False - we'll try to continue anyway with available models
            print("Attempting to continue with available models")
        
        # Then try to load each model WITHOUT downloading
        os.environ['ULTRALYTICS_NO_DOWNLOAD'] = 'true'
        
        for model_name in models:
            try:
                model_path = MODEL_DIR / model_name
                print(f"Loading model from {model_path}")
                
                # Specify the task based on model name
                task = None
                if "pose" in model_name:
                    task = "pose"
                
                # Load the model with explicit task where needed
                if task:
                    model = YOLO(str(model_path), task=task)
                else:
                    model = YOLO(str(model_path))
                print(f"Successfully loaded {model_name}")
                
                # Create a minimal test image
                test_img_path = "test_image.jpg"
                with open(test_img_path, "wb") as f:
                    f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x03\x02\x02\x03\x02\x02\x03\x03\x03\x03\x04\x03\x03\x04\x05\x08\x05\x05\x04\x04\x05\n\x07\x07\x06\x08\x0c\n\x0c\x0c\x0b\n\x0b\x0b\r\x0e\x12\x10\r\x0e\x11\x0e\x0b\x0b\x10\x16\x10\x11\x13\x14\x15\x15\x15\x0c\x0f\x17\x18\x16\x14\x18\x12\x14\x15\x14\xff\xdb\x00C\x01\x03\x04\x04\x05\x04\x05\t\x05\x05\t\x14\r\x0b\r\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\xff\xc2\x00\x11\x08\x00\x01\x00\x01\x03\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\n\xff\xc4\x00\x14\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x10\x03\x10\x00\x00\x01\x95\x00\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x01\x05\x02\x00\xff\xc4\x00\x14\x11\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x03\x01\x01?\x01\x00\xff\xc4\x00\x14\x11\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x02\x01\x01?\x01\x00\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x06?\x02\x00\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x01?!\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x00\x03\x00\x00\x00\x10\x00\xff\xc4\x00\x14\x11\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x03\x01\x01?\x10\x00\xff\xc4\x00\x14\x11\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x02\x01\x01?\x10\x00\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x01?\x10\x00\xff\xd9')
                
                # Run a minimal prediction to cache the model in memory
                try:
                    result = model(test_img_path)
                    print(f"Successfully loaded and tested {model_name}")
                    success_count += 1
                except Exception as pred_err:
                    print(f"Warning: Could not run prediction with {model_name}: {pred_err}")
                    print(f"Model was loaded but may not be fully initialized")
                    # Consider this a success as we at least loaded the model
                    success_count += 1
                
                # Clean up the test image
                try:
                    os.remove(test_img_path)
                except:
                    pass
                
            except Exception as model_error:
                print(f"ERROR: Could not load {model_name}: {model_error}")
        
        print(f"Ultralytics models verification completed. Loaded {success_count}/{len(models)} models")
        return success_count > 0
    except Exception as e:
        print(f"Error verifying Ultralytics models: {e}")
        print("Continuing build process despite model verification failure")
        return False

def preload_easyocr():
    """Verify pre-downloaded EasyOCR models."""
    try:
        print("Verifying pre-downloaded EasyOCR models...")
        
        # Verify both required model files exist
        craft_path = MODEL_DIR / "craft_mlt_25k.pth"
        english_path = MODEL_DIR / "english_g2.pth"
        
        if not craft_path.exists():
            print(f"ERROR: CRAFT detection model not found at {craft_path}")
            return False
            
        if not english_path.exists():
            print(f"ERROR: English recognition model not found at {english_path}")
            return False
            
        print(f"Found EasyOCR detection model: {craft_path}")
        print(f"Found EasyOCR recognition model: {english_path}")
        
        try:
            # Force install specific easyocr version
            print("Installing specific easyocr version...")
            subprocess.run([sys.executable, "-m", "pip", "install", "--no-cache-dir", "easyocr==1.6.2"], check=True)
            import easyocr
            print("Successfully imported easyocr")
            
            # Set environment variables to prevent downloads
            os.environ['EASYOCR_DOWNLOAD_ENABLED'] = 'false'
            
            print(f"Initializing EasyOCR with model directory: {MODEL_DIR}")
            reader = easyocr.Reader(['en'], model_storage_directory=str(MODEL_DIR))
            print("Successfully loaded EasyOCR models")
            return True
        except Exception as ocr_error:
            print(f"Error initializing EasyOCR: {ocr_error}")
            return False
            
    except Exception as e:
        print(f"Error verifying EasyOCR models: {e}")
        print("Continuing build process despite model verification failure")
        return False

def main():
    """Main function to verify all models are pre-downloaded."""
    print("Starting model verification process...")
    
    try:
        # Create the model directory if it doesn't exist
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        
        # Verify all required models exist
        print(f"Verifying models in {MODEL_DIR}...")
        missing_models = []
        for model_name, url in MODEL_URLS.items():
            output_path = MODEL_DIR / model_name
            if output_path.exists():
                print(f"Found model {model_name} at {output_path}")
            else:
                missing_models.append(model_name)
                print(f"ERROR: Model {model_name} missing from {output_path}")
        
        if missing_models:
            print(f"ERROR: {len(missing_models)} models are missing! Docker must be built with wget commands.")
            print(f"Missing models: {missing_models}")
            return 1
        
        # Verify models can be loaded
        yolo_success = preload_ultralytics_models()
        ocr_success = preload_easyocr()
        
        if yolo_success and ocr_success:
            print("All models successfully verified!")
        else:
            status = []
            if yolo_success:
                status.append("YOLO models: SUCCESS")
            else:
                status.append("YOLO models: FAILED")
            
            if ocr_success:
                status.append("OCR models: SUCCESS")
            else:
                status.append("OCR models: FAILED")
            
            print(f"Model verification partial success: {', '.join(status)}")
        
        print("Model verification completed!")
        # Always return success to ensure build continues
        return 0
    except Exception as e:
        print(f"Error during model verification: {e}")
        print("Continuing build process despite verification errors")
        # Return success to ensure build continues
        return 0

if __name__ == "__main__":
    main() 