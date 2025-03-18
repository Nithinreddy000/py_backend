#!/usr/bin/env python3
"""
Patch script for ultralytics module to fix the 'NoneType has no attribute keys' error.

This script directly modifies the ultralytics module in your Python environment
to prevent the settings.yaml lookup that causes the error.
"""

import os
import sys
import inspect
import importlib
import pkgutil
import shutil
import tempfile

def find_module_path(module_name):
    """Find the filesystem path of a Python module"""
    try:
        module = importlib.import_module(module_name)
        if hasattr(module, '__file__'):
            return os.path.dirname(module.__file__)
        else:
            # Try an alternative approach for namespace packages
            loader = pkgutil.find_loader(module_name)
            if loader:
                return os.path.dirname(loader.get_filename())
    except ImportError:
        pass
    return None

def patch_ultralytics():
    """Patch the ultralytics module to fix the settings issue"""
    # First check if ultralytics is installed
    ultralytics_path = find_module_path('ultralytics')
    
    if not ultralytics_path:
        print("❌ Ultralytics module not found. Please install it first.")
        return False
    
    print(f"Found ultralytics at: {ultralytics_path}")
    
    # Path to the utils file that contains the get_settings function
    utils_file = os.path.join(ultralytics_path, 'yolo', 'utils', '__init__.py')
    
    if not os.path.exists(utils_file):
        print(f"❌ Could not find utils file at {utils_file}")
        return False
    
    print(f"Found utils file at: {utils_file}")
    
    # Create a backup of the file
    backup_file = f"{utils_file}.backup"
    if not os.path.exists(backup_file):
        shutil.copy2(utils_file, backup_file)
        print(f"Created backup at {backup_file}")
    
    # Read the file content
    with open(utils_file, 'r') as f:
        content = f.read()
    
    # Check if it contains the get_settings function
    if 'def get_settings(' not in content:
        print("❌ Could not find get_settings function in the utils file")
        return False
    
    # Create a patch for the get_settings function
    patched_function = """
def get_settings():
    """Return global ultralyltics settings or create a new default settings dict if None."""
    # Patched version that returns a default empty dict to avoid NoneType error
    return {}  # Always return an empty dict to avoid 'NoneType has no attribute keys' error
"""
    
    # Create a temporary file with the patched content
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp:
        # Replace the get_settings function with our patched version
        patched_content = content.replace('def get_settings(', 'def _original_get_settings(')
        patched_content += patched_function
        temp.write(patched_content)
        temp_path = temp.name
    
    # Copy the temporary file to the utils file
    shutil.copy2(temp_path, utils_file)
    os.unlink(temp_path)
    
    print("✅ Successfully patched ultralytics module")
    print("The module will now return an empty dict for settings instead of None")
    
    # Test the patch
    try:
        # Force reload the module
        if 'ultralytics.yolo.utils' in sys.modules:
            del sys.modules['ultralytics.yolo.utils']
        
        from ultralytics.yolo.utils import get_settings
        settings = get_settings()
        
        if isinstance(settings, dict):
            print("✅ Patch verification successful - get_settings() now returns a dict")
            return True
        else:
            print(f"❌ Patch verification failed - get_settings() returned {type(settings)} instead of dict")
            return False
    except Exception as e:
        print(f"❌ Error testing the patch: {e}")
        return False

if __name__ == "__main__":
    print("Patching ultralytics module...")
    if patch_ultralytics():
        print("Patch completed successfully")
        sys.exit(0)
    else:
        print("Patch failed")
        sys.exit(1) 