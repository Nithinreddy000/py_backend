FROM python:3.9-slim

WORKDIR /app

# Copy requirements file first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create models directory if it doesn't exist
RUN mkdir -p models/z-anatomy

# Create a volume for the models directory
VOLUME /app/models

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Expose the port
EXPOSE 8080

# Run the application with Gunicorn
CMD gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 8 --timeout 120 app:app 