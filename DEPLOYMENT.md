# Deploying to Google Cloud Run with Flask/Werkzeug Compatibility Fix

This document provides instructions for deploying the application to Google Cloud Run with a fix for the Flask/Werkzeug compatibility issue that causes the `url_quote` import error.

## The Issue

The error occurs because of incompatibility between Flask and Werkzeug versions:

```
ImportError: cannot import name 'url_quote' from 'werkzeug.urls'
```

This happens when Flask expects `url_quote` to be available in Werkzeug, but the installed version of Werkzeug does not provide this function.

## Option 1: Deploy Using the Patched Dockerfile

The simplest approach is to use the patched Dockerfile that installs compatible versions of Flask and Werkzeug and applies necessary patches.

### Steps

1. **Build the Docker image using the patched Dockerfile:**

```bash
cd final100/python_backend
docker build -t gcr.io/[YOUR-PROJECT-ID]/backend:fixed -f Dockerfile.patched .
```

2. **Push the image to Google Container Registry:**

```bash
docker push gcr.io/[YOUR-PROJECT-ID]/backend:fixed
```

3. **Deploy to Google Cloud Run:**

```bash
gcloud run deploy backend \
  --image gcr.io/[YOUR-PROJECT-ID]/backend:fixed \
  --platform managed \
  --region us-central1 \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 0 \
  --max-instances 10 \
  --timeout 600 \
  --concurrency 80 \
  --allow-unauthenticated
```

## Option 2: Patch the Existing Deployment using Cloud Build

If you prefer not to rebuild the entire container, you can create a custom build step that applies the patch:

### Steps

1. **Create a cloudbuild.yaml file:**

```yaml
steps:
  # Pull the existing image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['pull', 'gcr.io/[YOUR-PROJECT-ID]/backend:latest']

  # Create a container from the image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['create', '--name', 'backend_container', 'gcr.io/[YOUR-PROJECT-ID]/backend:latest']

  # Copy the patch script into the container
  - name: 'gcr.io/cloud-builders/docker'
    args: ['cp', 'patch_werkzeug.py', 'backend_container:/app/']

  # Commit the changes to a new image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['commit', 'backend_container', 'gcr.io/[YOUR-PROJECT-ID]/backend:patched']

  # Apply packages and patches inside the container
  - name: 'gcr.io/cloud-builders/docker'
    args: ['run', '--rm', 'gcr.io/[YOUR-PROJECT-ID]/backend:patched', 'pip', 'install', '--no-cache-dir', 'flask==2.0.3', 'werkzeug==2.0.3', 'flask-cors==3.0.10', 'blinker==1.6.2']

  # Run the patch script
  - name: 'gcr.io/cloud-builders/docker'
    args: ['run', '--rm', 'gcr.io/[YOUR-PROJECT-ID]/backend:patched', 'python', '/app/patch_werkzeug.py']

  # Push the patched image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/[YOUR-PROJECT-ID]/backend:patched']

  # Deploy to Cloud Run
  - name: 'gcr.io/cloud-builders/gcloud'
    args:
      - 'run'
      - 'deploy'
      - 'backend'
      - '--image'
      - 'gcr.io/[YOUR-PROJECT-ID]/backend:patched'
      - '--platform'
      - 'managed'
      - '--region'
      - 'us-central1'
      - '--memory'
      - '2Gi'
      - '--cpu'
      - '2'
      - '--timeout'
      - '600'
      - '--allow-unauthenticated'

images:
  - 'gcr.io/[YOUR-PROJECT-ID]/backend:patched'
```

2. **Run the Cloud Build:**

```bash
gcloud builds submit --config cloudbuild.yaml .
```

## Option 3: Manual Fix via Google Cloud Run Console

If you have access to the Google Cloud Run console and want to apply a quick fix:

1. Go to the Google Cloud Run console
2. Select your service
3. Click "Edit & Deploy New Revision"
4. Under "Container" section, click "CONTAINERS" tab
5. Add the following to the "Command" field:
   ```
   /bin/bash,-c,pip install flask==2.0.3 werkzeug==2.0.3 flask-cors==3.0.10 blinker==1.6.2 && echo "from urllib.parse import quote as url_quote" >> /usr/local/lib/python3.9/site-packages/werkzeug/urls.py && exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 600 app:app
   ```
6. Click "Deploy"

## Verifying the Fix

After deployment, you can verify the fix by:

1. Checking the service logs for any further errors
2. Making a request to the health endpoint: `https://[YOUR-SERVICE-URL]/health`

## Troubleshooting

If you continue to experience issues:

1. **Check logs:** Use `gcloud run logs read --service backend` to view detailed logs
2. **Check versions:** Use `gcloud run services describe backend` to confirm the correct image is deployed
3. **Test locally:** Run the Docker image locally to verify it works before deploying:
   ```bash
   docker run -p 8080:8080 gcr.io/[YOUR-PROJECT-ID]/backend:fixed
   ```

## Additional Notes

- The compatible versions for this fix are Flask 2.0.3 and Werkzeug 2.0.3
- Always use `blinker` package if you're using Sentry SDK with Flask
- Consider pinning all dependency versions in your requirements.txt to prevent future compatibility issues 