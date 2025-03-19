#!/bin/bash
#
# Script to fix Flask and Werkzeug compatibility issues
# Run this on your deployed server to resolve the url_quote import error
#

set -e
echo "Flask/Werkzeug Compatibility Fix Script"
echo "======================================"

# Create a file to indicate we're fixing packages
touch /app/fixing_packages.txt

# Install compatible versions of Flask and Werkzeug
echo "Installing compatible versions of Flask and Werkzeug..."
pip uninstall -y flask werkzeug
pip install --no-cache-dir flask==2.0.3 werkzeug==2.0.3 flask-cors==3.0.10

# Verify the installations
echo "Verifying installations..."
python -c "import flask; print(f'Flask version: {flask.__version__}')"
python -c "import werkzeug; print(f'Werkzeug version: {werkzeug.__version__}')"

# Check if url_quote is now available
echo "Testing url_quote import..."
python -c "from werkzeug.urls import url_quote; print('✅ url_quote import successful')" || echo "❌ url_quote import still failing"

# If url_quote is still not available, try an alternative version
if ! python -c "from werkzeug.urls import url_quote" 2>/dev/null; then
    echo "Trying alternative versions of Werkzeug..."
    pip uninstall -y werkzeug
    pip install --no-cache-dir werkzeug==2.0.2
    python -c "import werkzeug; print(f'Updated Werkzeug version: {werkzeug.__version__}')"
    python -c "from werkzeug.urls import url_quote 2>/dev/null; print('✅ url_quote import successful')" || echo "❌ url_quote still not available, trying to patch..."
    
    # If all else fails, create a patch
    if ! python -c "from werkzeug.urls import url_quote" 2>/dev/null; then
        echo "Creating patch for url_quote..."
        SITE_PACKAGES=$(python -c "import site; print(site.getsitepackages()[0])")
        WERKZEUG_URLS="$SITE_PACKAGES/werkzeug/urls.py"
        
        # Check if the file exists
        if [ -f "$WERKZEUG_URLS" ]; then
            # Add url_quote as alias for quote
            echo "
# Patched for Flask compatibility
try:
    from .urls import quote as url_quote
except ImportError:
    from urllib.parse import quote as url_quote
" >> "$WERKZEUG_URLS"
            echo "✅ Patched $WERKZEUG_URLS"
        else
            echo "❌ Could not find $WERKZEUG_URLS to patch"
        fi
    fi
fi

# Remove the fixing flag
rm -f /app/fixing_packages.txt

# Check for gunicorn and restart if needed
echo "Checking for running Gunicorn process..."
GUNICORN_PID=$(pgrep -f gunicorn)

if [ -n "$GUNICORN_PID" ]; then
    echo "Found Gunicorn process with PID: $GUNICORN_PID"
    echo "Would you like to restart Gunicorn? (y/n)"
    read -r answer
    
    if [ "$answer" = "y" ] || [ "$answer" = "Y" ]; then
        echo "Stopping Gunicorn..."
        kill -TERM $GUNICORN_PID
        
        # Wait for process to stop
        sleep 5
        
        echo "Starting Gunicorn with fixed configuration..."
        cd /app
        
        # Apply environment variables from fix_tensorflow.sh if it exists
        if [ -f "/app/setup_env.sh" ]; then
            source /app/setup_env.sh
        fi
        
        gunicorn --bind 0.0.0.0:${PORT:-8080} \
            --workers 1 \
            --threads 8 \
            --timeout 600 \
            --graceful-timeout 300 \
            --keep-alive 5 \
            --max-requests 1000 \
            --max-requests-jitter 50 \
            --worker-class gthread \
            --log-level info \
            app:app &
            
        echo "Started Gunicorn with PID: $!"
    else
        echo "Gunicorn not restarted. The changes will take effect on the next restart."
    fi
else
    echo "No Gunicorn process found. The changes will take effect when you start the application."
fi

echo "Fix completed! Flask/Werkzeug compatibility issues should be resolved." 