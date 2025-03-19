#!/bin/bash
#
# Comprehensive Fix Script for Backend Issues
# This script fixes both TensorFlow and Flask/Werkzeug compatibility issues
#

set -e
echo "====================================================="
echo "    Comprehensive Backend Fix Script"
echo "====================================================="
echo ""

# Create indicator file
touch /app/fixing_backend.txt

echo "Step 1: Apply critical environment variables"
echo "--------------------------------------------"
export TF_ENABLE_ONEDNN_OPTS=0
export TF_CPP_MIN_LOG_LEVEL=3
export NO_BF16_INSTRUCTIONS=1
export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
export DISABLE_TENSOR_FLOAT_32_EXECUTION=1
export DISABLE_TRANSFORMERS=true
export CUDA_VISIBLE_DEVICES=-1
export PYTHONNOUSERSITE=1

# Create a script to apply these environment variables on startup
echo "Creating environment setup script..."
cat > /app/setup_env.sh << 'EOL'
#!/bin/bash
export TF_ENABLE_ONEDNN_OPTS=0
export TF_CPP_MIN_LOG_LEVEL=3
export NO_BF16_INSTRUCTIONS=1
export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
export DISABLE_TENSOR_FLOAT_32_EXECUTION=1
export DISABLE_TRANSFORMERS=true
export CUDA_VISIBLE_DEVICES=-1
export PYTHONNOUSERSITE=1
EOL
chmod +x /app/setup_env.sh

echo "Creating disable_tf.txt file to disable TensorFlow initialization..."
echo "TensorFlow and Transformers are explicitly disabled for compatibility reasons." > /app/disable_tf.txt
chmod 644 /app/disable_tf.txt

echo ""
echo "Step 2: Fix Flask and Werkzeug compatibility"
echo "-------------------------------------------"
echo "Installing compatible versions of Flask and Werkzeug..."
pip uninstall -y flask werkzeug
pip install --no-cache-dir flask==2.0.3 werkzeug==2.0.3 flask-cors==3.0.10 blinker==1.6.2

# Verify the installations
echo "Verifying Flask/Werkzeug installations..."
python -c "import flask; print(f'Flask version: {flask.__version__}')"
python -c "import werkzeug; print(f'Werkzeug version: {werkzeug.__version__}')"

# Check if url_quote is available
echo "Testing url_quote import..."
if ! python -c "from werkzeug.urls import url_quote" 2>/dev/null; then
    echo "url_quote not found, trying werkzeug 2.0.2..."
    pip uninstall -y werkzeug
    pip install --no-cache-dir werkzeug==2.0.2
    
    # If still not available, patch werkzeug
    if ! python -c "from werkzeug.urls import url_quote" 2>/dev/null; then
        echo "Creating patch for url_quote..."
        SITE_PACKAGES=$(python -c "import site; print(site.getsitepackages()[0])")
        WERKZEUG_URLS="$SITE_PACKAGES/werkzeug/urls.py"
        
        # Add url_quote as alias
        echo '
# Patched for Flask compatibility
from urllib.parse import quote as url_quote
' >> "$WERKZEUG_URLS"
        echo "Patched Werkzeug urls.py"
    fi
fi

echo ""
echo "Step 3: Fix TensorFlow and transformers issues"
echo "---------------------------------------------"
echo "Removing problematic TensorFlow installation..."
pip uninstall -y tensorflow tensorflow-estimator tensorflow-io-gcs-filesystem

echo "Installing compatible versions of libraries..."
pip install --no-cache-dir torch==1.13.1 torchvision==0.14.1 --index-url https://download.pytorch.org/whl/cpu
pip install --no-cache-dir "numpy<1.24.0" --force-reinstall
pip install --no-cache-dir ultralytics==8.0.196 --no-deps
pip install --no-cache-dir "transformers<4.30.0" --no-deps
pip install --no-cache-dir "tokenizers<0.14.0"

# Create a custom patch for transformers
echo "Creating patch for transformers library..."
cat > /tmp/patch_transformers.py << 'EOL'
"""
Patch script to disable TensorFlow in transformers
"""
import os
import sys

try:
    # Find the transformers package
    import transformers
    transformers_dir = os.path.dirname(transformers.__file__)
    
    # Create a patched dummy_tf_objects.py file
    patch_file = os.path.join(transformers_dir, "utils", "dummy_tf_objects.py")
    with open(patch_file, "w") as f:
        f.write("""
def is_tf_available():
    return False

def is_torch_available():
    return True
""")
    print(f"Created patch file: {patch_file}")
    
    # Patch import_utils.py to disable TensorFlow
    import_utils_file = os.path.join(transformers_dir, "utils", "import_utils.py")
    try:
        with open(import_utils_file, "r") as f:
            content = f.read()
        
        # Replace the _tf_available function
        if "def _tf_available():" in content:
            content = content.replace(
                "def _tf_available():",
                "def _tf_available():\n    return False"
            )
            
            with open(import_utils_file, "w") as f:
                f.write(content)
            print(f"Patched {import_utils_file}")
        else:
            print(f"Could not find _tf_available function in {import_utils_file}")
    except Exception as e:
        print(f"Error patching {import_utils_file}: {e}")
    
    # Create a __init__.py patch to import functions from the proper place
    init_file = os.path.join(transformers_dir, "utils", "__init__.py")
    try:
        with open(init_file, "a") as f:
            f.write("""
# Patch to ensure TF functions are properly imported
from .dummy_tf_objects import is_tf_available, is_torch_available
""")
        print(f"Patched {init_file}")
    except Exception as e:
        print(f"Error patching {init_file}: {e}")
    
    print("Successfully patched transformers library")
except ImportError:
    print("Transformers not installed, skipping patch")
except Exception as e:
    print(f"Error patching transformers: {e}")
EOL

# Run the patch script
echo "Applying transformers patch..."
python /tmp/patch_transformers.py

echo ""
echo "Step 4: Testing imports"
echo "---------------------"
echo "Testing Flask import..."
python -c "import flask; print('✅ Flask import successful')" || echo "❌ Flask import failed"

echo "Testing Werkzeug urls import..."
python -c "from werkzeug.urls import url_quote; print('✅ url_quote import successful')" || echo "❌ url_quote import failed"

echo "Testing PyTorch import..."
python -c "import torch; print(f'✅ PyTorch {torch.__version__} import successful')" || echo "❌ PyTorch import failed"

echo "Testing transformers import without TensorFlow..."
python -c "import transformers; print(f'✅ Transformers {transformers.__version__} import successful'); print(f'  TensorFlow available: {transformers.is_tf_available()}')" || echo "❌ Transformers import failed"

# Remove the fixing flag
rm -f /app/fixing_backend.txt

echo ""
echo "Step 5: Restart Gunicorn"
echo "----------------------"
echo "Checking for running Gunicorn process..."
GUNICORN_PID=$(pgrep -f gunicorn)

if [ -n "$GUNICORN_PID" ]; then
    echo "Found Gunicorn process with PID: $GUNICORN_PID"
    echo "Would you like to restart Gunicorn with the fixes applied? (y/n)"
    read -r answer
    
    if [ "$answer" = "y" ] || [ "$answer" = "Y" ]; then
        echo "Stopping Gunicorn..."
        kill -TERM $GUNICORN_PID
        
        # Wait for process to stop
        sleep 5
        
        echo "Starting Gunicorn with fixed configuration..."
        cd /app
        source /app/setup_env.sh
        
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

echo ""
echo "====================================================="
echo "    Fix process completed!"
echo "====================================================="
echo ""
echo "All compatibility issues should now be resolved."
echo "If you continue to experience problems, please restart the server." 