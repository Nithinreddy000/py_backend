#!/bin/bash
#
# Script to fix TensorFlow compatibility issues
# Run this on your deployed server to resolve TensorFlow errors
#

set -e
echo "TensorFlow Compatibility Fix Script"
echo "=================================="

# Create a file to disable TensorFlow in the application
echo "Creating disable_tf.txt file to disable TensorFlow initialization..."
touch /app/disable_tf.txt
chmod 644 /app/disable_tf.txt

# Set critical environment variables
export TF_ENABLE_ONEDNN_OPTS=0
export TF_CPP_MIN_LOG_LEVEL=3
export NO_BF16_INSTRUCTIONS=1
export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
export DISABLE_TENSOR_FLOAT_32_EXECUTION=1
export DISABLE_TRANSFORMERS=true
export CUDA_VISIBLE_DEVICES=-1

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
EOL
chmod +x /app/setup_env.sh

# Fix the transformers installation if necessary
echo "Attempting to fix transformers installation..."
pip install --no-cache-dir "transformers<4.30.0" --no-deps
pip install --no-cache-dir "tokenizers<0.14.0"

# Fix TensorFlow installation
echo "Removing problematic TensorFlow installation..."
pip uninstall -y tensorflow tensorflow-estimator tensorflow-io-gcs-filesystem

echo "Installing compatible TensorFlow version..."
pip install --no-cache-dir "tensorflow-cpu<2.11.0" "numpy<1.24.0" --force-reinstall

# Create a custom version of disable_tensorflow.py
echo "Creating patch for transformers library..."
cat > /tmp/disable_tf_patch.py << 'EOL'
"""
Patch to disable TensorFlow in transformers
"""
import sys
import os

# Find the transformers directory
import transformers
transformers_dir = os.path.dirname(transformers.__file__)

# Override the is_tf_available function
patch_code = """
def is_tf_available():
    return False

def is_torch_available():
    return True
"""

# Apply the patch
patch_file = os.path.join(transformers_dir, "utils", "dummy_tf_objects.py")
with open(patch_file, "w") as f:
    f.write(patch_code)

print(f"Applied patch to {patch_file}")

# Also override the import_utils.py file
import_utils_file = os.path.join(transformers_dir, "utils", "import_utils.py")
try:
    with open(import_utils_file, "r") as f:
        content = f.read()
    
    # Replace the _tf_available function
    content = content.replace(
        "def _tf_available():",
        "def _tf_available():\n    return False"
    )
    
    with open(import_utils_file, "w") as f:
        f.write(content)
    
    print(f"Applied patch to {import_utils_file}")
except Exception as e:
    print(f"Error patching {import_utils_file}: {e}")
EOL

# Run the patch script
echo "Applying transformers patch..."
python /tmp/disable_tf_patch.py

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

echo "Fix completed! TensorFlow compatibility issues should be resolved." 