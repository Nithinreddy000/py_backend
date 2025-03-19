#!/usr/bin/env python3
"""
Werkzeug URL Quote Patch

This script patches the werkzeug.urls module to include the url_quote function,
which is needed by Flask but might be missing in some versions of Werkzeug.

Usage:
  python patch_werkzeug.py

Note: This script can be run directly in the container or during the build process.
"""

import os
import sys
import importlib
import site

def find_werkzeug_urls():
    """Find the werkzeug.urls module path."""
    try:
        import werkzeug
        werkzeug_dir = os.path.dirname(werkzeug.__file__)
        urls_path = os.path.join(werkzeug_dir, "urls.py")
        
        if os.path.exists(urls_path):
            return urls_path
        
        # If not found directly, try to find in site-packages
        for site_dir in site.getsitepackages():
            possible_path = os.path.join(site_dir, "werkzeug", "urls.py")
            if os.path.exists(possible_path):
                return possible_path
        
        return None
    except ImportError:
        print("Werkzeug is not installed.")
        return None


def check_url_quote_exists():
    """Check if url_quote is already defined in werkzeug.urls."""
    try:
        from werkzeug.urls import url_quote
        print("url_quote is already defined in werkzeug.urls")
        return True
    except ImportError:
        print("url_quote is not defined in werkzeug.urls")
        return False


def patch_werkzeug_urls(urls_path):
    """Patch the werkzeug.urls module to include url_quote."""
    try:
        print(f"Patching {urls_path}...")
        
        # Read the current content
        with open(urls_path, "r") as f:
            content = f.read()
        
        # Check if url_quote is already defined
        if "def url_quote" in content or "quote as url_quote" in content:
            print("url_quote is already defined in the file. No need to patch.")
            return False
        
        # Add the url_quote alias to the end of the file
        with open(urls_path, "a") as f:
            f.write("\n# Patched for Flask compatibility\nfrom urllib.parse import quote as url_quote\n")
        
        print("Successfully patched werkzeug.urls to include url_quote")
        return True
    except Exception as e:
        print(f"Failed to patch werkzeug.urls: {e}")
        return False


def verify_patch():
    """Verify that the patch worked by importing url_quote."""
    try:
        # Reload werkzeug module
        import werkzeug
        importlib.reload(werkzeug)
        
        # Try to import url_quote
        from werkzeug.urls import url_quote
        print("✓ Verification successful: url_quote can be imported")
        return True
    except ImportError as e:
        print(f"✗ Verification failed: {e}")
        return False


def main():
    """Main function."""
    print("=== Werkzeug URL Quote Patch ===")
    
    # Find the werkzeug.urls module
    urls_path = find_werkzeug_urls()
    if not urls_path:
        print("Could not find werkzeug.urls module.")
        return False
    
    print(f"Found werkzeug.urls at: {urls_path}")
    
    # Check if url_quote already exists
    if check_url_quote_exists():
        print("No patching needed.")
        return True
    
    # Apply the patch
    patched = patch_werkzeug_urls(urls_path)
    
    # Verify the patch
    if patched:
        verified = verify_patch()
        if verified:
            print("\nPatch successfully applied and verified!")
        else:
            print("\nPatch was applied but verification failed.")
        return verified
    
    return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 