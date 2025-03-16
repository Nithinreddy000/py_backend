"""
Script to check that all necessary imports are available.
This helps diagnose import errors during deployment.
"""

import sys
import os

def check_imports():
    """Check that all required modules can be imported."""
    print("Checking required imports...")
    
    required_modules = [
        'flask',
        'flask_cors',
        'werkzeug',
        'numpy',
        'pandas',
        'firebase_admin',
        'google.cloud',
        'requests',
        'tensorflow',
        'matplotlib',
        'mistralai',
        'fastapi',
        'uvicorn',
        'pymeshlab',
        'reportlab',
        'scipy',
        'trimesh',
        'markdown',
        'fitz',  # PyMuPDF
        'cv2',   # OpenCV
        'ultralytics',
        'supervision',
        'easyocr',
        'cloudinary',
        'torch',
        'torchvision',
        'mediapipe',
        'tqdm',
        'pytube',
        'moviepy',
        'av',
        'ffmpeg',
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
            print(f"✓ {module}")
        except ImportError as e:
            print(f"✗ {module} - Error: {e}")
            missing_modules.append(module)
    
    if missing_modules:
        print("\nMissing modules:")
        for module in missing_modules:
            print(f"  - {module}")
        print("\nTry installing them with:")
        print(f"pip install {' '.join(missing_modules)}")
        return False
    else:
        print("\nAll required modules are available!")
        return True

if __name__ == "__main__":
    success = check_imports()
    sys.exit(0 if success else 1) 