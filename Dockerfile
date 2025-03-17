FROM python:3.9-slim

WORKDIR /app

# Copy requirements file first for better caching
COPY requirements.txt .

# Install required system dependencies including OpenCV dependencies and Blender
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
    blender \
    xvfb \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Download spaCy English model
RUN python -m spacy download en_core_web_sm

# Copy the rest of the application
COPY . .

# Create models directory if it doesn't exist
RUN mkdir -p models/z-anatomy models/z-anatomy/output

# Create a volume for the models directory
VOLUME /app/models

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV FLASK_APP=app.py
ENV FLASK_DEBUG=0
ENV CORS_ENABLED=true
ENV DISABLE_ML_MODELS=false
ENV LAZY_LOAD_MODELS=true

# Expose the port
EXPOSE 8080

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:${PORT}/health || exit 1

# Make the Blender installation script executable
RUN chmod +x install_blender.sh

# Verify Blender installation
RUN blender --version

# Run the application with Gunicorn with increased timeout
CMD gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 8 --timeout 300 --graceful-timeout 300 --keep-alive 5 app:app 