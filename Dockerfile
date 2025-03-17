FROM python:3.9-slim

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