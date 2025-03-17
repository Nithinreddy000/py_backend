"""
Simplified entry point for Render deployment.
This loads the main app and ensures it binds to the right port.
"""

import os
import sys
import traceback
from flask import Flask, jsonify
from flask_cors import CORS

# Create a simple placeholder app in case imports fail
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

@app.route('/')
def health_check():
    return "Flask server is running. Main application status: " + get_app_status()

@app.route('/status')
def status():
    return jsonify({
        "status": "running",
        "main_app_loaded": main_app_loaded,
        "error": error_details if not main_app_loaded else None,
        "version": "1.0.0",
    })

# Global variables to track app status
main_app_loaded = False
error_details = None

# Try to import the main app
try:
    print("Importing main application...")
    # Add the current directory to the path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # First check if we need to install any missing dependencies
    missing_deps = []
    try:
        import transformers
    except ImportError:
        print("Transformers library missing, will be installed automatically")
        missing_deps.append("transformers>=4.28.0")
    
    # Install missing dependencies if needed
    if missing_deps:
        import subprocess
        print(f"Installing missing dependencies: {missing_deps}")
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing_deps)
        print("Dependencies installed successfully")
    
    # Import the app from app.py
    from app import app as main_app
    
    # Import our CORS middleware
    try:
        from cors_middleware import apply_cors
        
        # Apply CORS middleware to main app if needed
        if os.environ.get('CORS_ENABLED', 'true').lower() == 'true':
            print("Applying enhanced CORS middleware...")
            main_app.after_request(add_cors_headers)
        
    except ImportError:
        print("CORS middleware not available, using default CORS")
    
    # Replace our placeholder app with the main app
    app = main_app
    main_app_loaded = True
    print("Main application imported successfully!")
except Exception as e:
    # If the import fails, we'll keep our simple app instead
    error_details = f"{str(e)}\n{traceback.format_exc()}"
    print(f"Error importing main application: {str(e)}")
    print(traceback.format_exc())
    print("Starting with minimal placeholder app instead")
    
    @app.route('/error')
    def error_details_route():
        return f"<h1>Error loading main application</h1><pre>{error_details}</pre>"

# Add CORS headers to all responses
def add_cors_headers(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With,Accept,Origin,Range')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Expose-Headers', 'Content-Length, Content-Type, Content-Disposition, Last-Modified, Accept-Ranges, ETag')
    return response

def get_app_status():
    return "fully loaded" if main_app_loaded else "running in fallback mode"

# This is only used when running directly with Python, not with Gunicorn
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    print(f"Starting server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False) 