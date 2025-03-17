FROM python:3.9-slim

# Install system dependencies required for OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Make startup script executable
RUN chmod +x startup.sh

# Environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV CORS_ENABLED=true

# Run the startup script
CMD ["./startup.sh"] 