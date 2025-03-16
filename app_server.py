"""
Simple test script to verify our Flask server binds to the correct port.
This helps diagnose issues with Render deployment.
"""

import os
from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return "Hello World! Server is running correctly."

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    print(f"Starting server on port {port}")
    app.run(host='0.0.0.0', port=port) 