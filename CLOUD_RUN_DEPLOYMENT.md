# Deploying to Google Cloud Run

This document provides instructions for deploying the backend service to Google Cloud Run.

## Prerequisites

1. Google Cloud SDK installed and configured
2. Docker installed and configured
3. Google Cloud project with Cloud Run API enabled
4. Permissions to deploy to Cloud Run

## Deployment Steps

### 1. Build and Push the Docker Image

```bash
# Navigate to the python_backend directory
cd final100/python_backend

# Build the Docker image
docker build -t gcr.io/YOUR_PROJECT_ID/athlete-management-backend:latest .

# Push the image to Google Container Registry
docker push gcr.io/YOUR_PROJECT_ID/athlete-management-backend:latest
```

### 2. Deploy to Cloud Run

```bash
# Deploy to Cloud Run
gcloud run deploy athlete-management-backend \
  --image gcr.io/YOUR_PROJECT_ID/athlete-management-backend:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 600 \
  --concurrency 10
```

### 3. Environment Variables (Optional)

You can set environment variables during deployment:

```bash
gcloud run deploy athlete-management-backend \
  --image gcr.io/YOUR_PROJECT_ID/athlete-management-backend:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 600 \
  --concurrency 10 \
  --set-env-vars="DISABLE_ML_MODELS=false,LAZY_LOAD_MODELS=true"
```

## Troubleshooting

### Container Fails to Start

If the container fails to start, check the following:

1. **Logs**: Check the Cloud Run logs for errors:
   ```bash
   gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=athlete-management-backend" --limit=50
   ```

2. **Memory Issues**: If the service is running out of memory, increase the memory allocation when deploying.

3. **Timeout Issues**: If operations take longer than expected, increase the timeout when deploying.

4. **Port Configuration**: Ensure the application listens on the port specified by the `PORT` environment variable. Our application now correctly reads this from the environment.

### Testing Locally Before Deployment

To test the Docker container locally before deployment:

```bash
# Build the image
docker build -t athlete-management-backend:local .

# Run the container locally
docker run -p 8080:8080 -e PORT=8080 athlete-management-backend:local
```

Then access the application at http://localhost:8080

## Best Practices

1. **Scaling**: Cloud Run automatically scales based on traffic. Configure min and max instances if needed.
2. **Memory Usage**: Monitor memory usage and adjust the allocation as needed.
3. **Cold Starts**: Be aware of cold start times, especially for ML-heavy applications.
4. **Error Handling**: Ensure the application handles errors gracefully and returns appropriate status codes.
5. **Health Checks**: Implement a health check endpoint to monitor application health. 