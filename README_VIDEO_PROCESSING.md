# Enhanced Video Processing System

This module provides advanced video processing capabilities for the Athlete Management System, focusing on athlete performance analysis through pose detection, jersey number recognition, and Fitbit data integration.

## Features

### 1. Advanced Pose Detection
- Uses YOLOv8x-pose for high-accuracy pose detection
- Tracks 17 key body points for detailed motion analysis
- Visualizes pose skeleton with color-coded body parts
- Calculates performance metrics based on pose data

### 2. Jersey Number Recognition
- Enhanced OCR with preprocessing for better jersey number detection
- Associates detected jersey numbers with athlete profiles
- Tracks athletes across video frames using ByteTrack algorithm
- Displays athlete names and metrics based on jersey identification

### 3. Fitbit Data Integration
- Generates realistic Fitbit sensor data based on athlete movement
- Includes heart rate, steps, calories, distance, force, and acceleration
- Adapts data generation to different sport types (running, swimming, weightlifting)
- Visualizes Fitbit metrics alongside performance data

### 4. Sport-Specific Metrics
- **Running**: stride length, cadence, vertical oscillation, speed
- **Swimming**: stroke rate, stroke length, efficiency, speed
- **Weightlifting**: form quality, power, velocity, range of motion

### 5. Enhanced Video Output
- Annotated video with bounding boxes around athletes
- Color-coded pose skeleton visualization
- Performance metrics overlay
- Athlete identification with jersey numbers

## Usage

### Processing a Match Video

1. Upload a match video through the Match Management interface
2. Select the sport type and athletes participating in the match
3. The system will process the video in the background
4. Once processing is complete, the annotated video and metrics will be available in the Coach Dashboard

### Viewing Processed Videos

1. Navigate to the Coach Dashboard
2. The "Processed Match Videos" section displays the latest processed videos
3. Select an athlete from the dropdown to view their specific performance
4. The video player shows the annotated video with pose detection
5. Performance metrics and Fitbit data are displayed below the video

## Technical Implementation

### Video Processing Pipeline

1. **Video Upload**: Video is uploaded to temporary storage
2. **Pose Detection**: YOLOv8x-pose model detects athlete poses
3. **Athlete Tracking**: ByteTrack algorithm tracks athletes across frames
4. **Jersey Detection**: Enhanced OCR detects jersey numbers
5. **Metrics Calculation**: Performance metrics are calculated based on pose data
6. **Fitbit Data Generation**: Fake Fitbit data is generated based on movement
7. **Video Annotation**: Processed video is annotated with pose skeleton and metrics
8. **Storage**: Processed video is uploaded to Cloudinary
9. **Database Update**: Performance metrics and Fitbit data are stored in Firestore

### Key Components

- `process_match_video`: API endpoint for video processing
- `process_video_background`: Background thread for video processing
- `process_video`: Main video processing function
- `detect_jersey_numbers`: Jersey number detection with enhanced OCR
- `update_athlete_metrics`: Updates performance metrics based on pose data
- `update_fitbit_data`: Generates and updates fake Fitbit data
- `annotate_frame`: Annotates video frames with pose skeleton and metrics

## Requirements

See `requirements.txt` for the full list of dependencies. Key packages include:

- ultralytics (YOLOv8)
- supervision (ByteTrack)
- opencv-python
- easyocr
- cloudinary
- mediapipe
- torch/torchvision
- ffmpeg-python
- moviepy

### Installation

We provide installation scripts to help you set up the required dependencies:

#### Installing to D Drive (Recommended for Windows)
If you're experiencing disk space issues on your C drive, you can install the dependencies to the D drive:

```
# Run the batch file
install_to_d_drive.bat
```

This will:
1. Create a virtual environment at D:/venvs/ams_video_processing
2. Install all dependencies to that location
3. Create activation scripts for the virtual environment

To use the virtual environment:
```
# Activate the virtual environment
activate_venv.bat

# When finished, deactivate the virtual environment
deactivate
```

#### Standard Installation
If you have enough space on your system drive:

##### Windows
```
# Run the batch file
install_dependencies.bat
```

##### Linux/Mac
```
# Make the script executable
chmod +x install_dependencies.sh

# Run the script
./install_dependencies.sh
```

#### Manual Installation
If you prefer to install the dependencies manually, you can use pip:
```
# Update pip
python -m pip install --upgrade pip

# Install dependencies
python -m pip install -r requirements.txt
```

If you encounter any issues with the installation, try installing the packages individually:
```
python -m pip install numpy requests setuptools wheel future
python -m pip install firebase-admin google-cloud-storage google-cloud-firestore
python -m pip install torch torchvision tensorflow scikit-learn
python -m pip install opencv-python ultralytics supervision easyocr cloudinary
python -m pip install mediapipe pytube moviepy av ffmpeg-python
```

If you encounter any issues during installation, please refer to the [Troubleshooting Guide](TROUBLESHOOTING.md).

### Testing

We provide test scripts to verify that the video processing functionality works correctly:

#### Testing with D Drive Virtual Environment
If you installed to the D drive:
```
# Run the batch file
test_with_venv.bat
```

#### Standard Testing
If you used the standard installation:

##### Windows
```
# Run the batch file
test_video_processing.bat
```

##### Linux/Mac
```
# Make the script executable
chmod +x test_video_processing.sh

# Run the script
./test_video_processing.sh
```

#### Manual Testing
You can also run the test script directly:
```
python test_video_processing.py
```

This will:
1. Create a sample video
2. Test YOLO object detection
3. Verify that the core components are working correctly

### Running the Server

To start the Python backend server:

#### Running with D Drive Virtual Environment
If you installed to the D drive:
```
# Run the batch file
start_server_with_venv.bat
```

#### Standard Server Start
If you used the standard installation:

##### Windows
```
# Run the batch file
start_server.bat
```

##### Linux/Mac
```
# Make the script executable
chmod +x start_server.sh

# Run the script
./start_server.sh
```

#### Manual Start
You can also start the server directly:
```
python app.py
```

The server will start on port 5000 by default. You can access the API at http://localhost:5000.

## Future Enhancements

- Real Fitbit API integration for actual sensor data
- Machine learning for personalized performance insights
- Team formation analysis and tactical recommendations
- Injury risk prediction based on movement patterns
- Real-time video processing for immediate feedback 