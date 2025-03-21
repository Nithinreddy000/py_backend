# Base image
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    blender \
    python3-opencv \
    libglib2.0-0 \
    libgl1-mesa-glx \
    xvfb \
    wget \
    curl \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Make startup script executable
RUN chmod +x /app/start_server.sh

# Verify blender installation
RUN blender --version

# Set environment variables for memory optimization
ENV MALLOC_ARENA_MAX=2
ENV TF_FORCE_GPU_ALLOW_GROWTH=true
ENV TF_CPP_MIN_LOG_LEVEL=2
ENV CUDA_VISIBLE_DEVICES="-1"
ENV OMP_NUM_THREADS=1
ENV MKL_NUM_THREADS=1

# Cloud Run will set PORT environment variable
# Default to 8080 for local testing
ENV PORT=8080

# Expose the port the app runs on
EXPOSE 8080

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -f http://localhost:${PORT}/health || exit 1

# Start the server using the startup script
CMD ["/app/start_server.sh"] 