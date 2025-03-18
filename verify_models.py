#!/usr/bin/env python3
"""
Model Verification Script

This script verifies that the ML models and libraries are compatible and working correctly.
Run this script to check for issues with ultralytics, EasyOCR, and other ML dependencies.
"""

import os
import sys
import subprocess
import pkg_resources
import importlib.util
from pathlib import Path


def print_header(title):
    """Print a formatted header."""
    print("\n" + "=" * 80)
    print(f" {title} ".center(80, "="))
    print("=" * 80)


def check_package_version(package_name, min_version=None, exact_version=None):
    """Check if a package is installed and verify its version."""
    try:
        package = pkg_resources.get_distribution(package_name)
        print(f"✅ {package_name} is installed (version: {package.version})")
        
        if exact_version and package.version != exact_version:
            print(f"⚠️  WARNING: {package_name} version {package.version} doesn't match required version {exact_version}")
            return False
        
        if min_version and pkg_resources.parse_version(package.version) < pkg_resources.parse_version(min_version):
            print(f"⚠️  WARNING: {package_name} version {package.version} is older than required version {min_version}")
            return False
            
        return True
    except pkg_resources.DistributionNotFound:
        print(f"❌ {package_name} is not installed")
        return False


def verify_ultralytics():
    """Verify ultralytics installation and model loading."""
    print_header("Checking ultralytics")
    
    # Check compatible torch version for ultralytics 8.0.196
    torch_ok = check_package_version("torch", exact_version="1.13.1")
    if not torch_ok:
        print("⚠️  PyTorch version needs to be 1.13.1 for compatibility with ultralytics 8.0.196")
        print("Consider reinstalling: pip install torch==1.13.1 torchvision==0.14.1 --force-reinstall")
    
    if not check_package_version("ultralytics", exact_version="8.0.196"):
        print("Consider reinstalling: pip install ultralytics==8.0.196 --force-reinstall")
    
    try:
        print("\nAttempting to import YOLO...")
        from ultralytics import YOLO
        print("✅ Successfully imported YOLO")
        
        # Check model directories
        model_dir = Path(os.environ.get('YOLO_MODEL_PATH', '/root/.config/ultralytics/models'))
        print(f"\nChecking model directory: {model_dir}")
        if not model_dir.exists():
            print(f"❌ Model directory {model_dir} does not exist")
            os.makedirs(model_dir, exist_ok=True)
            print(f"Created directory {model_dir}")
        
        # Try to load models directly from file path, avoiding ultralytics model loading API
        # if there are compatibility issues
        print("\nChecking for model files...")
        models = ["yolov8n.pt", "yolov8n-pose.pt"]
        for model_name in models:
            model_path = model_dir / model_name
            if model_path.exists():
                try:
                    model_size = model_path.stat().st_size / (1024 * 1024)  # Size in MB
                    print(f"✅ Found {model_name} ({model_size:.1f} MB)")
                except Exception as e:
                    print(f"⚠️  Error checking {model_name}: {str(e)}")
            else:
                print(f"❌ Model file not found: {model_path}")
        
        print("\nAttempting to load models with YOLO...")
        if torch_ok:
            try:
                # Only attempt to load models if torch is compatible
                import torch
                model = YOLO("yolov8n.pt")
                print(f"✅ Successfully loaded {model}")
                
                pose_model = YOLO("yolov8n-pose.pt")
                print(f"✅ Successfully loaded {pose_model}")
            except Exception as e:
                print(f"❌ Failed to load models via YOLO API: {str(e)}")
                print("  This may be due to PyTorch/ultralytics version compatibility issues.")
        else:
            print("⚠️  Skipping model loading with YOLO API due to PyTorch version compatibility issues")
            
    except ImportError as e:
        print(f"❌ Failed to import YOLO: {str(e)}")
    except Exception as e:
        print(f"❌ Unexpected error with ultralytics: {str(e)}")


def verify_easyocr():
    """Verify EasyOCR installation and model loading."""
    print_header("Checking EasyOCR")
    
    check_package_version("easyocr")
    
    try:
        print("\nAttempting to import EasyOCR...")
        import easyocr
        print("✅ Successfully imported EasyOCR")
        
        # Check model directories
        model_dir = Path(os.environ.get('EASYOCR_MODULE_PATH', '/app/models/easyocr'))
        print(f"\nChecking model directory: {model_dir}")
        if not model_dir.exists():
            print(f"❌ Model directory {model_dir} does not exist")
            os.makedirs(model_dir, exist_ok=True)
            print(f"Created directory {model_dir}")
        else:
            # Check if directory has files
            files = list(model_dir.glob('*'))
            if len(files) > 0:
                print(f"✅ Found {len(files)} files in model directory")
                for f in files[:5]:  # Show first 5 files
                    try:
                        size = f.stat().st_size / (1024 * 1024)  # Size in MB
                        print(f"  - {f.name} ({size:.1f} MB)")
                    except Exception as e:
                        print(f"  - {f.name} (error getting size: {str(e)})")
                if len(files) > 5:
                    print(f"  ... and {len(files) - 5} more files")
            else:
                print("⚠️  Model directory exists but is empty")
        
        # Try to load reader only if directory has files
        if model_dir.exists() and len(list(model_dir.glob('*'))) > 0:
            print("\nAttempting to initialize EasyOCR Reader (this may take some time)...")
            try:
                reader = easyocr.Reader(['en'], model_storage_directory=str(model_dir), download_enabled=False)
                print("✅ Successfully initialized EasyOCR Reader")
            except Exception as e:
                print(f"❌ Failed to initialize EasyOCR Reader: {str(e)}")
                print("  Trying again with download_enabled=True...")
                try:
                    reader = easyocr.Reader(['en'], model_storage_directory=str(model_dir), download_enabled=True)
                    print("✅ Successfully initialized EasyOCR Reader with downloads enabled")
                except Exception as e2:
                    print(f"❌ Still failed to initialize EasyOCR Reader: {str(e2)}")
        else:
            print("\n⚠️  Skipping EasyOCR Reader initialization as model directory is empty or missing")
            
    except ImportError as e:
        print(f"❌ Failed to import EasyOCR: {str(e)}")
    except Exception as e:
        print(f"❌ Unexpected error with EasyOCR: {str(e)}")


def verify_blender():
    """Verify Blender installation."""
    print_header("Checking Blender")
    
    try:
        result = subprocess.run(['which', 'blender'], capture_output=True, text=True)
        if result.returncode == 0:
            blender_path = result.stdout.strip()
            print(f"✅ Blender found at: {blender_path}")
            
            # Get version
            version_result = subprocess.run(['blender', '--version'], capture_output=True, text=True)
            if version_result.returncode == 0:
                print(f"Blender version info: {version_result.stdout.strip()}")
            else:
                print(f"⚠️  Could not get Blender version: {version_result.stderr}")
        else:
            print("❌ Blender not found in PATH")
            
            # Check common installation paths
            common_paths = [
                '/opt/blender/blender-2.93.13-linux-x64/blender',
                '/usr/local/bin/blender',
                '/usr/bin/blender'
            ]
            
            for path in common_paths:
                if os.path.exists(path):
                    print(f"ℹ️  Blender found at alternative location: {path}")
                    
                    # Try to get version
                    try:
                        version_result = subprocess.run([path, '--version'], capture_output=True, text=True)
                        if version_result.returncode == 0:
                            print(f"Blender version info: {version_result.stdout.strip()}")
                        else:
                            print(f"⚠️  Could not get Blender version: {version_result.stderr}")
                    except Exception as e:
                        print(f"⚠️  Error checking Blender version: {str(e)}")
                        
                    break
    except Exception as e:
        print(f"❌ Error checking Blender: {str(e)}")


def verify_system_libraries():
    """Verify required system libraries."""
    print_header("Checking System Libraries")
    
    libraries = [
        "libGL.so.1",        # OpenGL
        "libSM.so.6",        # X11 Session Management
        "libglib-2.0.so.0",  # GLib
        "libgomp.so.1"       # OpenMP
    ]
    
    for lib in libraries:
        try:
            result = subprocess.run(['ldconfig', '-p'], capture_output=True, text=True)
            if lib in result.stdout:
                print(f"✅ Found library: {lib}")
            else:
                print(f"❌ Library not found: {lib}")
        except Exception as e:
            print(f"⚠️  Could not check for library {lib}: {str(e)}")


def verify_environment_variables():
    """Verify essential environment variables."""
    print_header("Checking Environment Variables")
    
    essential_vars = [
        "YOLO_MODEL_PATH",
        "EASYOCR_MODULE_PATH",
        "TF_ENABLE_ONEDNN_OPTS",
        "TF_CPP_MIN_LOG_LEVEL",
        "PYTHONUNBUFFERED"
    ]
    
    for var in essential_vars:
        value = os.environ.get(var)
        if value:
            print(f"✅ {var} = {value}")
        else:
            print(f"⚠️  {var} is not set")


def main():
    """Main verification function."""
    print_header("MODEL VERIFICATION TOOL")
    print("This script checks compatibility of ML models and libraries.")
    
    verify_ultralytics()
    verify_easyocr()
    verify_blender()
    verify_system_libraries()
    verify_environment_variables()
    
    print_header("VERIFICATION COMPLETE")
    

if __name__ == "__main__":
    main() 