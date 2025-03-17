"""
Simple script to test CORS headers on your deployment.
You can run this locally to verify that CORS is properly configured.
"""

import requests
import sys
import os

def check_cors_headers(url):
    """Check if a URL has proper CORS headers."""
    print(f"Testing CORS for: {url}")
    
    # Try a normal GET request
    print("Testing GET request...")
    try:
        response = requests.get(url)
        print(f"Status: {response.status_code}")
        
        # Check for CORS headers
        cors_headers = {k: v for k, v in response.headers.items() if 'access-control' in k.lower()}
        if cors_headers:
            print("✅ CORS headers found in GET response:")
            for k, v in cors_headers.items():
                print(f"  - {k}: {v}")
        else:
            print("❌ No CORS headers found in GET response")
    except Exception as e:
        print(f"❌ Error making GET request: {e}")
    
    # Try an OPTIONS preflight request
    print("\nTesting OPTIONS preflight request...")
    try:
        headers = {
            'Origin': 'http://localhost:51742',
            'Access-Control-Request-Method': 'GET',
            'Access-Control-Request-Headers': 'X-Requested-With'
        }
        response = requests.options(url, headers=headers)
        print(f"Status: {response.status_code}")
        
        # Check for CORS headers
        cors_headers = {k: v for k, v in response.headers.items() if 'access-control' in k.lower()}
        if cors_headers:
            print("✅ CORS headers found in OPTIONS response:")
            for k, v in cors_headers.items():
                print(f"  - {k}: {v}")
        else:
            print("❌ No CORS headers found in OPTIONS response")
    except Exception as e:
        print(f"❌ Error making OPTIONS request: {e}")

if __name__ == "__main__":
    # Default URLs to test
    default_base_url = "https://py-backend-4crp.onrender.com"
    
    # Use the provided URL or default
    base_url = sys.argv[1] if len(sys.argv) > 1 else default_base_url
    
    # Test the main API endpoint
    check_cors_headers(f"{base_url}/health")
    
    # Test a model endpoint
    check_cors_headers(f"{base_url}/model/models/z-anatomy/Muscular.glb")
    
    print("\nCORS testing completed. If you see '❌ No CORS headers found', your API is not properly configured for CORS.") 