#!/usr/bin/env python3
"""
Download Models Script

This script handles downloading the necessary ML models, managing version
compatibility issues between PyTorch and ultralytics.
"""

import os
import sys
import torch
import shutil
import subprocess
import requests
from pathlib import Path


def print_header(title):
    """Print a formatted header."""
    print("\n" + "=" * 80)
    print(f" {title} ".center(80, "="))
    print("=" * 80)


def get_torch_version():
    """Get the installed torch version."""
    return torch.__version__


def download_file(url, output_path):
    """Download a file from URL to the specified path."""
    try:
        print(f"Downloading {url} to {output_path}...")
        response = requests.get(url, stream=True)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024 * 1024  # 1MB
        downloaded = 0

        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=block_size):
                if chunk:  # filter out keep-alive chunks
                    f.write(chunk)
                    downloaded += len(chunk)
                    progress = int(50 * downloaded / total_size) if total_size > 0 else 0
                    sys.stdout.write(f"\r[{'=' * progress}{' ' * (50 - progress)}] {downloaded/1024/1024:.1f}MB/{total_size/1024/1024:.1f}MB")
                    sys.stdout.flush()

        print("\nDownload complete!")
        return True
    except Exception as e:
        print(f"Error downloading file: {str(e)}")
        return False


def download_yolo_models():
    """Download YOLO models directly without using ultralytics API."""
    print_header("Downloading YOLO Models")
    
    # Create directories
    models_dir = Path("/root/.config/ultralytics/models")
    models_dir.mkdir(parents=True, exist_ok=True)
    
    # Model URLs
    yolo_models = {
        "yolov8n.pt": "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt",
        "yolov8n-pose.pt": "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n-pose.pt"
    }
    
    for model_name, url in yolo_models.items():
        output_path = models_dir / model_name
        if output_path.exists():
            print(f"Model {model_name} already exists at {output_path}")
        else:
            success = download_file(url, output_path)
            if success:
                print(f"Downloaded {model_name} to {output_path}")
            else:
                print(f"Failed to download {model_name}")
    
    # Set permissions
    try:
        subprocess.run(['chmod', '-R', '777', str(models_dir.parent)])
        print(f"Set permissions on {models_dir.parent}")
    except Exception as e:
        print(f"Error setting permissions: {str(e)}")


def download_easyocr_models():
    """Download EasyOCR models."""
    print_header("Downloading EasyOCR Models")
    
    try:
        import easyocr
        model_dir = Path("/app/models/easyocr")
        model_dir.mkdir(parents=True, exist_ok=True)
        
        print("Initializing EasyOCR Reader (this will download models)...")
        reader = easyocr.Reader(['en'], model_storage_directory=str(model_dir), download_enabled=True)
        print("EasyOCR models downloaded successfully")
        
        # Set permissions
        subprocess.run(['chmod', '-R', '777', str(model_dir)])
        print(f"Set permissions on {model_dir}")
    except Exception as e:
        print(f"Error downloading EasyOCR models: {str(e)}")


def setup_environment_variables():
    """Setup environment variables for model paths."""
    print_header("Setting Environment Variables")
    
    env_vars = {
        "EASYOCR_MODULE_PATH": "/app/models/easyocr",
        "YOLO_MODEL_PATH": "/root/.config/ultralytics/models"
    }
    
    for var, value in env_vars.items():
        os.environ[var] = value
        print(f"Set {var}={value}")


def main():
    """Main function."""
    print_header("MODEL DOWNLOAD TOOL")
    print(f"PyTorch version: {get_torch_version()}")
    
    # Create necessary directories
    for directory in [
        "/app/models/yolo",
        "/app/models/easyocr",
        "/app/models/z-anatomy/output",
        "/app/fallback_models",
        "/root/.config/ultralytics",
        "/root/.EasyOCR",
        "/root/.cache/torch"
    ]:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {directory}")
    
    # Download models
    download_yolo_models()
    download_easyocr_models()
    
    # Setup environment
    setup_environment_variables()
    
    # Create flag file
    Path("/app/models/.preloaded").touch()
    print("Created .preloaded flag file")
    
    print_header("DOWNLOAD COMPLETE")
    

if __name__ == "__main__":
    main() 