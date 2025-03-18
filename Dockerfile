FROM python:3.9-slim

WORKDIR /app

# Copy requirements file first for better caching
COPY requirements.txt .

# Install required system dependencies including OpenCV dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    curl \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    ffmpeg \
    git \
    xvfb \
    xauth \
    mesa-utils \
    libgl1 \
    libgles2 \
    libosmesa6 \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install a specific portable version of Blender (2.93 LTS) which has better compatibility
RUN mkdir -p /opt/blender && \
    cd /opt/blender && \
    wget -q https://download.blender.org/release/Blender2.93/blender-2.93.13-linux-x64.tar.xz && \
    tar -xf blender-2.93.13-linux-x64.tar.xz && \
    rm blender-2.93.13-linux-x64.tar.xz && \
    ln -s /opt/blender/blender-2.93.13-linux-x64/blender /usr/local/bin/blender

# Set environment variables for Blender
ENV BLENDER_PATH=/opt/blender/blender-2.93.13-linux-x64/blender

# Upgrade pip and install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Fixed: Create ultralytics settings directory and file with proper permissions
# Create for both root and non-root users to ensure it works regardless of user context
RUN mkdir -p /root/.config/ultralytics && \
    echo "{}" > /root/.config/ultralytics/settings.yaml && \
    chmod 644 /root/.config/ultralytics/settings.yaml && \
    mkdir -p /.config/ultralytics && \
    echo "{}" > /.config/ultralytics/settings.yaml && \
    chmod 777 /.config && \
    chmod 777 /.config/ultralytics && \
    chmod 666 /.config/ultralytics/settings.yaml

# Set environment variable to point to settings directory
ENV ULTRALYTICS_CONFIG_DIR=/root/.config/ultralytics

# Verify the ultralytics settings work by running a test script
RUN echo 'import yaml; from pathlib import Path; \
    settings_file = Path("/root/.config/ultralytics/settings.yaml"); \
    assert settings_file.exists(), "Settings file does not exist"; \
    settings = yaml.safe_load(settings_file.read_text()); \
    assert isinstance(settings, dict), "Settings must be a dictionary"; \
    print("✅ Ultralytics settings verified")' > verify_settings.py && \
    python verify_settings.py

# Download spaCy English model
RUN python -m spacy download en_core_web_sm

# Copy our patch scripts first so we can run them
COPY patch_ultralytics.py fix_ultralytics.py ./
RUN chmod +x patch_ultralytics.py fix_ultralytics.py

# Run our patch script to directly fix the ultralytics module
RUN python patch_ultralytics.py

# Copy the rest of the application
COPY . .

# Create an entrypoint script to ensure fixes are applied
RUN echo '#!/bin/bash\n\
# Run patch script to ensure ultralytics is fixed\n\
python patch_ultralytics.py\n\
python fix_ultralytics.py\n\
\n\
# Start the application\n\
exec "$@"' > /entrypoint.sh && \
    chmod +x /entrypoint.sh

# Make the run script executable
RUN chmod +x run.sh

# Create models directory if it doesn't exist
RUN mkdir -p models/z-anatomy models/z-anatomy/output

# Create fallback models directory
RUN mkdir -p fallback_models

# Create a volume for the models directory
VOLUME /app/models

# Verify the ultralytics fix works with the application code
RUN echo "print('Testing app import...')" > test_app_import.py && \
    echo "import app" >> test_app_import.py && \
    echo "print('App imported successfully')" >> test_app_import.py && \
    python test_app_import.py

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV FLASK_APP=app.py
ENV FLASK_DEBUG=0
ENV CORS_ENABLED=true
ENV DISABLE_ML_MODELS=false
ENV LAZY_LOAD_MODELS=true

# Verify Blender installation
RUN /usr/local/bin/blender --version

# Expose the port
EXPOSE 8080

# Add healthcheck with reduced interval for Cloud Run
HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -f http://localhost:${PORT}/health || exit 1

# Set the entrypoint to our script
ENTRYPOINT ["/entrypoint.sh"]

# Run the application directly with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--threads", "8", "--timeout", "300", "--log-level", "debug", "app:app"] 