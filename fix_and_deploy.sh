#!/bin/bash
#
# Script to build and deploy a fixed version of the backend to Google Cloud Run
#

set -e  # Exit on any error

# Configuration
PROJECT_ID="aerobic-oxide-447807-v2"
SERVICE_NAME="py-backend"
REGION="us-central1"
IMAGE_NAME="py-backend-fixed"
TAG="latest"

echo "====================================================="
echo "    Building and Deploying Fixed Backend"
echo "====================================================="
echo ""

# Step 1: Set Google Cloud project
echo "Setting Google Cloud project: $PROJECT_ID"
gcloud config set project $PROJECT_ID

# Step 2: Build the minimal patched Docker image
echo ""
echo "Building minimal patched Docker image..."
docker build -t gcr.io/$PROJECT_ID/$IMAGE_NAME:$TAG -f Dockerfile.minimal .

# Step 3: Push the image to Google Container Registry
echo ""
echo "Pushing image to Google Container Registry..."
docker push gcr.io/$PROJECT_ID/$IMAGE_NAME:$TAG

# Step 4: Deploy to Cloud Run with proper settings
echo ""
echo "Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$IMAGE_NAME:$TAG \
  --platform managed \
  --region $REGION \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 0 \
  --max-instances 10 \
  --timeout 600 \
  --concurrency 80 \
  --allow-unauthenticated \
  --set-env-vars="DISABLE_TRANSFORMERS=true,TF_ENABLE_ONEDNN_OPTS=0,TF_CPP_MIN_LOG_LEVEL=3" \
  --no-cpu-throttling \
  --cpu-boost

# Step 5: Display deployment status
echo ""
echo "Checking deployment status..."
gcloud run services describe $SERVICE_NAME --region $REGION --format="value(status.conditions)"

echo ""
echo "====================================================="
echo "    Deployment Completed"
echo "====================================================="
echo ""
echo "To check logs, run:"
echo "gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME' --limit=50"
echo ""
echo "To test the service, visit:"
echo "$(gcloud run services describe $SERVICE_NAME --region $REGION --format='value(status.url)')/health" 