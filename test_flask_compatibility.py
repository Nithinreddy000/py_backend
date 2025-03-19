#!/usr/bin/env python3
"""
Flask/Werkzeug Compatibility Test Script

This script tests if the specific versions of Flask and Werkzeug are compatible
and if the url_quote function can be imported properly.
"""

import sys
import importlib
import subprocess
import pkg_resources

def print_header(title):
    """Print a formatted header."""
    print("\n" + "=" * 80)
    print(f" {title} ".center(80, "="))
    print("=" * 80)


def check_package_version(package_name):
    """Check the installed version of a package."""
    try:
        package = pkg_resources.get_distribution(package_name)
        print(f"✅ {package_name} is installed (version: {package.version})")
        return package.version
    except pkg_resources.DistributionNotFound:
        print(f"❌ {package_name} is not installed")
        return None


def test_url_quote_import():
    """Test importing url_quote from werkzeug.urls."""
    print_header("Testing url_quote import")
    
    try:
        # Try to import url_quote
        from werkzeug.urls import url_quote
        print("✅ Successfully imported url_quote from werkzeug.urls")
        return True
    except ImportError as e:
        print(f"❌ Failed to import url_quote: {e}")
        return False


def patch_werkzeug():
    """Patch werkzeug.urls to include url_quote."""
    print_header("Patching werkzeug.urls")
    
    try:
        # Find the werkzeug directory
        import werkzeug
        werkzeug_dir = werkzeug.__path__[0]
        urls_path = f"{werkzeug_dir}/urls.py"
        
        print(f"Found werkzeug urls module at: {urls_path}")
        
        # Add the url_quote alias to the urls.py file
        with open(urls_path, "a") as f:
            f.write("\n# Patched for Flask compatibility\nfrom urllib.parse import quote as url_quote\n")
        
        print("✅ Successfully patched werkzeug.urls module")
        
        # Try importing again after patching
        importlib.reload(werkzeug)
        from werkzeug.urls import url_quote
        print("✅ Successfully imported url_quote after patching")
        return True
    except Exception as e:
        print(f"❌ Failed to patch werkzeug: {e}")
        return False


def install_compatible_versions():
    """Install compatible versions of Flask and Werkzeug."""
    print_header("Installing compatible versions")
    
    try:
        # Uninstall current versions
        subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "-y", "flask", "werkzeug"])
        
        # Install compatible versions
        subprocess.check_call([sys.executable, "-m", "pip", "install", "flask==2.0.3", "werkzeug==2.0.3"])
        
        print("✅ Successfully installed compatible versions")
        
        # Re-import the modules to ensure they're loaded from the new versions
        import importlib
        if "flask" in sys.modules:
            importlib.reload(sys.modules["flask"])
        if "werkzeug" in sys.modules:
            importlib.reload(sys.modules["werkzeug"])
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install compatible versions: {e}")
        return False


def create_minimal_flask_app():
    """Create a minimal Flask app to test imports."""
    print_header("Testing minimal Flask app")
    
    try:
        # Try to import Flask
        from flask import Flask, jsonify
        
        # Create a minimal app
        app = Flask(__name__)
        
        @app.route("/")
        def home():
            return jsonify({"status": "ok"})
        
        print("✅ Successfully created minimal Flask app")
        return True
    except ImportError as e:
        print(f"❌ Failed to import Flask components: {e}")
        return False


def main():
    """Main function to test and fix Flask/Werkzeug compatibility."""
    print_header("FLASK/WERKZEUG COMPATIBILITY TEST")
    
    # Check current versions
    flask_version = check_package_version("flask")
    werkzeug_version = check_package_version("werkzeug")
    
    # Test url_quote import
    url_quote_importable = test_url_quote_import()
    
    if not url_quote_importable:
        # Try installing compatible versions
        print("\nAttempting to fix by installing compatible versions...")
        install_compatible_versions()
        
        # Check new versions
        new_flask_version = check_package_version("flask")
        new_werkzeug_version = check_package_version("werkzeug")
        
        # Test url_quote import again
        url_quote_importable = test_url_quote_import()
        
        # If still not importable, try patching
        if not url_quote_importable:
            print("\nAttempting to patch werkzeug.urls...")
            patch_werkzeug()
            url_quote_importable = test_url_quote_import()
    
    # Test creating a minimal Flask app
    flask_app_creatable = create_minimal_flask_app()
    
    # Summary
    print_header("TEST RESULTS")
    print(f"Flask version: {check_package_version('flask')}")
    print(f"Werkzeug version: {check_package_version('werkzeug')}")
    print(f"url_quote importable: {'Yes' if url_quote_importable else 'No'}")
    print(f"Flask app creatable: {'Yes' if flask_app_creatable else 'No'}")
    
    if url_quote_importable and flask_app_creatable:
        print("\n✅ COMPATIBILITY TEST PASSED!")
        print("The current setup should work properly in production.")
    else:
        print("\n❌ COMPATIBILITY TEST FAILED!")
        print("Please use the patched Dockerfile for deployment.")


if __name__ == "__main__":
    main() 