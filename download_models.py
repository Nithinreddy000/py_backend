import os
import requests
import torch
import sys

def download_model(url, destination):
    """Download a model file if it doesn't already exist."""
    try:
        # Get the current directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        full_destination = os.path.join(current_dir, destination)
        
        print(f"Downloading model from {url} to {full_destination}...")
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(full_destination) if os.path.dirname(full_destination) else '.', exist_ok=True)
        
        # For PyTorch models, we can use torch.hub.download_url_to_file
        if url.endswith('.pt'):
            torch.hub.download_url_to_file(url, full_destination)
        else:
            # For other files, use requests
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            with open(full_destination, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        
        print(f"Successfully downloaded {full_destination}")
        return True
    except Exception as e:
        print(f"Error downloading model: {e}")
        return False

if __name__ == "__main__":
    # Print current directory for debugging
    print(f"Current directory: {os.getcwd()}")
    
    # Download YOLOv8x-pose model
    download_model(
        "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8x-pose.pt",
        "yolov8x-pose.pt"
    )
    
    # Download YOLOv8n-pose model (as backup/alternative)
    download_model(
        "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n-pose.pt",
        "yolov8n-pose.pt"
    )
    
    # Download YOLOv8n model
    download_model(
        "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt",
        "yolov8n.pt"
    )
    
    print("All models downloaded successfully!") 