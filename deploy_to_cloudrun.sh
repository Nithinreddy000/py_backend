#!/bin/bash
# Script to deploy the application to Cloud Run

set -e  # Exit on any error

# Configuration
PROJECT_ID=${PROJECT_ID:-"aerobic-oxide-447807-v2"}
SERVICE_NAME=${SERVICE_NAME:-"py-backend"}
REGION=${REGION:-"us-central1"}
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "Deploying to Cloud Run"
echo "======================"
echo "Project: $PROJECT_ID"
echo "Service: $SERVICE_NAME"
echo "Region: $REGION"
echo "Image: $IMAGE_NAME"
echo

# Ask for confirmation
read -p "Do you want to proceed with the deployment? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled"
    exit 0
fi

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "gcloud is not installed. Please install the Google Cloud SDK."
    exit 1
fi

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    echo "docker is not installed. Please install Docker."
    exit 1
fi

# Ensure user is logged in
echo "Checking gcloud authentication..."
gcloud auth print-access-token &> /dev/null || gcloud auth login

# Set the project
echo "Setting project..."
gcloud config set project $PROJECT_ID

# Build the image using the Cloud Run specific Dockerfile
echo "Building Docker image..."
docker build -t $IMAGE_NAME -f Dockerfile.cloudrun .

# Push the image to Google Container Registry
echo "Pushing image to Google Container Registry..."
docker push $IMAGE_NAME

# Deploy to Cloud Run
echo "Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --image=$IMAGE_NAME \
    --platform=managed \
    --region=$REGION \
    --memory=2Gi \
    --cpu=2 \
    --timeout=300 \
    --concurrency=80 \
    --max-instances=10 \
    --min-instances=1 \
    --allow-unauthenticated \
    --set-env-vars="DISABLE_ML_MODELS=true,LAZY_LOAD_MODELS=true,PYTHONUNBUFFERED=1"

echo
echo "Deployment complete!"
echo "Your service is available at: $(gcloud run services describe $SERVICE_NAME --region=$REGION --format='value(status.url)')"
echo
echo "To check the logs, run:"
echo "gcloud logging read \"resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME\" --limit=100" 