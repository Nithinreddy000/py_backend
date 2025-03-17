#!/usr/bin/env python
"""
Test script to verify model endpoint functionality
"""

import requests
import sys
import os

def test_model_endpoint(base_url, model_path):
    """Test if a model endpoint is accessible and returns proper content."""
    full_url = f"{base_url}/model/{model_path}"
    print(f"Testing model endpoint: {full_url}")
    
    try:
        response = requests.get(full_url)
        print(f"Status: {response.status_code}")
        
        # Check content type for GLB files
        if model_path.endswith('.glb'):
            content_type = response.headers.get('Content-Type', '')
            print(f"Content-Type: {content_type}")
            if 'model/gltf-binary' in content_type:
                print("✅ Correct Content-Type for GLB file")
            else:
                print("❌ Incorrect Content-Type for GLB file")
        
        # Check file size
        content_length = response.headers.get('Content-Length', '0')
        print(f"Content-Length: {content_length} bytes")
        
        if response.status_code == 200:
            print("✅ Model endpoint is accessible")
            return True
        else:
            print(f"❌ Model endpoint returned non-200 status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error accessing model endpoint: {e}")
        return False

if __name__ == "__main__":
    # Default values
    default_base_url = "https://py-backend-410293317488.us-central1.run.app"
    default_model_path = "models/z-anatomy/Muscular.glb"
    
    # Use the provided URL or default
    base_url = sys.argv[1] if len(sys.argv) > 1 else default_base_url
    model_path = sys.argv[2] if len(sys.argv) > 2 else default_model_path
    
    # Run tests
    test_model_endpoint(base_url, model_path)
    
    # Also test the specific path from the error message
    if "Muscular.glb" in model_path:
        test_path = "models/z-anatomy/output/painted_model_1741348403.glb"
        print(f"\nTesting problematic path from error message:")
        test_model_endpoint(base_url, test_path) 