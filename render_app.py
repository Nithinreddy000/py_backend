"""
Simplified entry point for Render deployment.
This loads the main app and ensures it binds to the right port.
"""

import os
import sys
from flask import Flask

# Create a simple placeholder app in case imports fail
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Flask server is running. Main application loading..."

# Try to import the main app
try:
    print("Importing main application...")
    # Add the current directory to the path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # Import the app from app.py
    from app import app as main_app
    
    # Replace our placeholder app with the main app
    app = main_app
    print("Main application imported successfully!")
except Exception as e:
    # If the import fails, we'll keep our simple app instead
    print(f"Error importing main application: {e}")
    print("Starting with minimal placeholder app instead")
    
    @app.route('/error')
    def error_details():
        return f"Error loading main application: {str(e)}"

# This is only used when running directly with Python, not with Gunicorn
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    print(f"Starting server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False) 