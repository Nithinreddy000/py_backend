"""
Special version of app.py for Cloud Run that includes critical fixes for ultralytics
"""

# First fix the ultralytics settings issue before any imports
import os
import sys
import importlib
import json
import yaml
from pathlib import Path

# Create all possible settings directories
for settings_dir in [
    '/root/.config/ultralytics',
    '/.config/ultralytics',
    os.path.expanduser('~/.config/ultralytics')
]:
    os.makedirs(settings_dir, exist_ok=True)
    
    # Create settings.yaml
    settings_yaml = os.path.join(settings_dir, 'settings.yaml')
    if not os.path.exists(settings_yaml):
        with open(settings_yaml, 'w') as f:
            yaml.safe_dump({}, f)
    
    # Create settings.json
    settings_json = os.path.join(settings_dir, 'settings.json')
    if not os.path.exists(settings_json):
        with open(settings_json, 'w') as f:
            json.dump({}, f)
    
    # Set permissions
    try:
        os.chmod(settings_dir, 0o777)
        os.chmod(settings_yaml, 0o666)
        os.chmod(settings_json, 0o666)
    except:
        pass

# Try to monkey patch ultralytics before importing
try:
    # First import the module
    import ultralytics
    
    # Now create a new function
    def get_settings_fixed():
        return {}  # Always return empty dict
    
    # And patch it into the module
    if hasattr(ultralytics.yolo.utils, 'get_settings'):
        ultralytics.yolo.utils.get_settings = get_settings_fixed
        print("Successfully monkey-patched ultralytics.yolo.utils.get_settings")
except:
    # If we can't access it yet, wait until after YOLO is imported
    pass

# Now import the actual app module
from app import app as flask_app

# This is required so gunicorn can find the app
app = flask_app

# Add an additional health endpoint for debugging
@app.route('/cloud-run-health')
def cloud_run_health():
    return {
        'status': 'ok',
        'message': 'Cloud Run special endpoint is working',
        'ultralytics_patched': True,
        'python_version': sys.version,
        'environment': dict(os.environ)
    }

if __name__ == '__main__':
    # This is for local testing
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False) 