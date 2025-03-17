#!/bin/bash
set -e

echo "Running startup script..."

# Install required packages
echo "Installing dependencies..."
pip install -r requirements.txt

# Install key NLP packages explicitly
echo "Installing NLP dependencies explicitly..."
pip install transformers>=4.28.0

# Skip the heavy import checks which were causing memory issues
echo "Skipping import checks due to memory constraints..."

# Create required directories
echo "Setting up directories..."
mkdir -p uploads
mkdir -p models/z-anatomy/output
mkdir -p mesh_data
mkdir -p temp_fixes

# Check if we need to apply CORS patches
if [ "$CORS_ENABLED" = "true" ]; then
  echo "CORS enhancement enabled - ensuring CORS headers will be added to all responses"
  
  # Make sure our CORS middleware is accessible
  if [ ! -f "cors_middleware.py" ]; then
    echo "Creating CORS middleware..."
    cat > cors_middleware.py << 'EOF'
"""
CORS middleware to ensure all responses have appropriate CORS headers.
"""
class CORSMiddleware:
    def __init__(self, app):
        self.app = app
        
    def __call__(self, environ, start_response):
        if environ['REQUEST_METHOD'] == 'OPTIONS':
            headers = [
                ('Access-Control-Allow-Origin', '*'),
                ('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS'),
                ('Access-Control-Allow-Headers', 'Authorization, Content-Type, Accept, Origin, X-Requested-With, Range'),
                ('Access-Control-Max-Age', '3600'),
                ('Access-Control-Expose-Headers', 'Content-Length, Content-Type, Content-Disposition, Last-Modified, Accept-Ranges, ETag')
            ]
            start_response('200 OK', headers)
            return [b'']
        
        def cors_start_response(status, headers, exc_info=None):
            headers_list = list(headers)
            has_cors_origin = False
            for name, value in headers_list:
                if name.lower() == 'access-control-allow-origin':
                    has_cors_origin = True
                    break
            
            if not has_cors_origin:
                headers_list.append(('Access-Control-Allow-Origin', '*'))
                headers_list.append(('Access-Control-Expose-Headers', 'Content-Length, Content-Type, Content-Disposition, Last-Modified, Accept-Ranges, ETag'))
            
            return start_response(status, headers_list, exc_info)
        
        return self.app(environ, cors_start_response)

def apply_cors(app):
    return CORSMiddleware(app)
EOF
  fi
else
  echo "CORS enhancement not enabled - using default CORS handling"
fi

# Only download the essential small model to conserve memory
echo "Downloading minimal model..."
python -c "
import os
import torch
print('Downloading minimal model...')
model_path = 'yolov8n.pt'
if not os.path.exists(model_path):
    torch.hub.download_url_to_file(
        'https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt',
        model_path
    )
    print(f'Downloaded {model_path}')
else:
    print(f'{model_path} already exists')
"

# Set any required environment variables
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Make sure PORT is set - Render sets this, but just to be safe
if [ -z "${PORT}" ]; then
  export PORT=10000
  echo "PORT not set, defaulting to 10000"
else
  echo "Using PORT: ${PORT}"
fi

# Print debugging information
echo "Environment:"
echo "- PYTHONPATH: $PYTHONPATH"
echo "- PORT: $PORT"
echo "- CORS_ENABLED: $CORS_ENABLED"
echo "- Current directory: $(pwd)"
echo "- Python version: $(python --version)"
echo "- Pip version: $(pip --version)"

# Start the server using our simplified entry point
echo "Starting server..."
gunicorn render_app:app --bind 0.0.0.0:$PORT --workers 1 --timeout 300 --log-level debug 