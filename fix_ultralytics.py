#!/usr/bin/env python3
"""
Script to fix the ultralytics settings issue where it throws:
AttributeError: 'NoneType' object has no attribute 'keys'

This happens because the ultralytics library expects a settings file at 
~/.config/ultralytics/settings.yaml but doesn't create it properly in some
container environments.

Run this script before starting your Flask application to ensure the settings
file exists.
"""

import os
import yaml
import sys

def fix_ultralytics_settings():
    """Create ultralytics settings directory and file if they don't exist"""
    # Get user home directory in a cross-platform way
    home_dir = os.path.expanduser('~')
    
    # Set up paths
    settings_dir = os.path.join(home_dir, '.config', 'ultralytics')
    settings_file = os.path.join(settings_dir, 'settings.yaml')
    
    print(f"Checking for ultralytics settings at: {settings_file}")
    
    # Create directory if it doesn't exist
    if not os.path.exists(settings_dir):
        print(f"Creating directory: {settings_dir}")
        os.makedirs(settings_dir, exist_ok=True)
    
    # Create settings file if it doesn't exist
    if not os.path.exists(settings_file):
        print(f"Creating settings file: {settings_file}")
        with open(settings_file, 'w') as f:
            # Write an empty dictionary as YAML
            yaml.safe_dump({}, f)
    else:
        print(f"Settings file already exists at: {settings_file}")
    
    # Verify file was created and is readable
    if os.path.exists(settings_file) and os.access(settings_file, os.R_OK):
        print("✅ Ultralytics settings file successfully created and readable")
        return True
    else:
        print("❌ Failed to create or access ultralytics settings file")
        return False

if __name__ == "__main__":
    print("Fixing ultralytics settings issue...")
    if fix_ultralytics_settings():
        print("Fix completed successfully")
        sys.exit(0)
    else:
        print("Fix failed")
        sys.exit(1) 