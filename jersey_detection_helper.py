import cv2
import numpy as np
import os
import traceback

class JerseyDetector:
    """
    Helper class for detecting jersey numbers in sports videos.
    This class provides improved jersey number detection for athlete identification.
    """
    
    def __init__(self, ocr_reader=None):
        """
        Initialize the jersey detector.
        
        Args:
            ocr_reader: An OCR reader instance (e.g., EasyOCR)
        """
        self.reader = ocr_reader
        self.jersey_map = {}  # Maps track_ids to jersey numbers
        self.confidence_map = {}  # Maps track_ids to confidence scores
        self.frame_count = 0
        self.detection_history = {}  # Tracks jersey number detections over time
        self.stable_associations = {}  # Track IDs that have been stably associated with a jersey
        self.frames_since_last_detection = {}  # Track frames since last detection for each jersey
        self.max_frames_to_keep_association = 30  # Keep track ID association for this many frames
    
    def set_ocr_reader(self, reader):
        """Set the OCR reader instance."""
        self.reader = reader
    
    def detect_jerseys(self, frame, detections, keypoints_list, athletes_data, frame_count):
        """
        Detect jersey numbers in the frame and associate them with tracked athletes.
        
        Args:
            frame: The video frame
            detections: List of detections with bounding boxes
            keypoints_list: List of keypoints for each detection
            athletes_data: Dictionary of athlete data
            frame_count: Current frame count
            
        Returns:
            List of detected jerseys with their associated box indices
        """
        self.frame_count = frame_count
        detected_jerseys = []
        
        try:
            # Extract valid jersey numbers from athletes_data
            valid_jersey_numbers = []
            for key in athletes_data:
                if isinstance(key, str) and key not in ['_jersey_map', '_frame_count']:
                    if key.isdigit() or (key.startswith('0') and key[1:].isdigit()):
                        valid_jersey_numbers.append(key)
            
            if not valid_jersey_numbers:
                valid_jersey_numbers = ['1', '2', '3']  # Default fallback
            
            print(f"Valid jersey numbers in this match: {valid_jersey_numbers}")
            
            # Increment frames since last detection for all jerseys
            for jersey in valid_jersey_numbers:
                if jersey not in self.frames_since_last_detection:
                    self.frames_since_last_detection[jersey] = 0
                else:
                    self.frames_since_last_detection[jersey] += 1
            
            # Check if we already have consistent track IDs for valid jersey numbers
            existing_track_ids = {}
            for jersey_number in valid_jersey_numbers:
                if jersey_number in athletes_data and athletes_data[jersey_number].get('track_id') is not None:
                    track_id = athletes_data[jersey_number]['track_id']
                    existing_track_ids[track_id] = jersey_number
                    
                    # If this is a stable association, maintain it
                    if track_id in self.stable_associations and self.stable_associations[track_id] == jersey_number:
                        print(f"Maintaining stable association: track_id {track_id} -> jersey {jersey_number}")
                        self.jersey_map[track_id] = jersey_number
                        self.confidence_map[track_id] = 1.0  # High confidence for stable associations
                        self.frames_since_last_detection[jersey_number] = 0
                        
                        # Add to detected jerseys list
                        detected_jerseys.append({
                            'jersey_number': jersey_number,
                            'track_id': track_id,
                            'confidence': 1.0,
                            'is_stable': True
                        })
            
            # Process each detection to find jersey numbers
            for i, detection in enumerate(detections):
                # Extract track_id from detection
                if len(detection) >= 6:  # Make sure we have track_id
                    x1, y1, x2, y2, conf, track_id = detection[:6]
                    track_id = int(track_id)
                    
                    # If this track_id is already stably associated, skip OCR detection
                    if track_id in self.stable_associations:
                        jersey_number = self.stable_associations[track_id]
                        if jersey_number in valid_jersey_numbers:
                            continue
                    
                    # Skip if we already have a high-confidence association for this track_id
                    if track_id in self.confidence_map and self.confidence_map[track_id] > 0.9:
                        continue
                    
                    # Extract the bounding box
                    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                    
                    # Expand the box slightly to ensure we capture the jersey
                    height = y2 - y1
                    width = x2 - x1
                    
                    # Focus on the upper body area where jersey numbers are typically located
                    jersey_y1 = max(0, y1 + int(height * 0.2))  # Start 20% down from the top of the person
                    jersey_y2 = min(frame.shape[0], y1 + int(height * 0.6))  # End at 60% down
                    jersey_x1 = max(0, x1 - int(width * 0.1))  # Expand width by 10% on each side
                    jersey_x2 = min(frame.shape[1], x2 + int(width * 0.1))
                    
                    # Extract the jersey region
                    jersey_region = frame[jersey_y1:jersey_y2, jersey_x1:jersey_x2]
                    
                    # If the region is too small, skip this detection
                    if jersey_region.size == 0 or jersey_region.shape[0] < 10 or jersey_region.shape[1] < 10:
                        continue
                        
                    # OCR failed or no text detected, try to find matching jersey
                    # Check if this detection is similar to any previous detection
                    for prev_track_id, jersey in self.jersey_map.items():
                        if jersey in valid_jersey_numbers:
                            # Only try to match with valid jerseys
                            continue
                    
                    # If we haven't assigned a jersey to this track_id yet, assign one based on position
                    if track_id not in self.jersey_map and valid_jersey_numbers:
                        # Sort detections by x-coordinate (left to right)
                        detection_idx = sorted(range(len(detections)), 
                                              key=lambda idx: (int(detections[idx][0]) + int(detections[idx][2])) / 2 
                                              if len(detections[idx]) >= 4 else float('inf'))
                        
                        # Find position of current detection in the sorted list
                        pos = detection_idx.index(i) if i in detection_idx else -1
                        
                        # Determine jersey number based on position
                        if pos >= 0 and pos < len(valid_jersey_numbers):
                            probable_jersey = valid_jersey_numbers[pos]
                            
                            # Check if this jersey is already assigned
                            is_jersey_assigned = any(j == probable_jersey for j in self.jersey_map.values())
                            if not is_jersey_assigned:
                                self.jersey_map[track_id] = probable_jersey
                                self.confidence_map[track_id] = 0.7
                                
                                print(f"Position-based assignment: track_id {track_id} -> jersey {probable_jersey}")
                                
                                # Add to detection history
                                if track_id not in self.detection_history:
                                    self.detection_history[track_id] = {}
                                if probable_jersey not in self.detection_history[track_id]:
                                    self.detection_history[track_id][probable_jersey] = 0
                                self.detection_history[track_id][probable_jersey] += 1
                                
                                # Add to detected jerseys list
                                detected_jerseys.append({
                                    'jersey_number': probable_jersey,
                                    'box_index': i,
                                    'track_id': track_id,
                                    'confidence': 0.7,
                                    'is_position_based': True
                                })
                                
                                # Reset frames since last detection
                                self.frames_since_last_detection[probable_jersey] = 0
            
            # If we have fewer detections than valid jersey numbers, make sure all jerseys are assigned
            if len(detections) <= len(valid_jersey_numbers):
                # Get unassigned jerseys
                assigned_jerseys = set(self.jersey_map.values())
                unassigned_jerseys = [j for j in valid_jersey_numbers if j not in assigned_jerseys]
                
                # Get unassigned track IDs
                assigned_track_ids = set(self.jersey_map.keys())
                unassigned_track_ids = [int(det[5]) for det in detections 
                                       if len(det) >= 6 and int(det[5]) not in assigned_track_ids]
                
                # Assign unassigned jerseys to unassigned track IDs
                for i, track_id in enumerate(unassigned_track_ids):
                    if i < len(unassigned_jerseys):
                        jersey_number = unassigned_jerseys[i]
                        self.jersey_map[track_id] = jersey_number
                        self.confidence_map[track_id] = 0.7
                        
                        print(f"Assigned unassigned jersey {jersey_number} to track_id {track_id}")
                        
                        # Add to detected jerseys list
                        detected_jerseys.append({
                            'jersey_number': jersey_number,
                            'track_id': track_id,
                            'confidence': 0.7,
                            'is_assigned': True
                        })
                        
                        # Reset frames since last detection
                        self.frames_since_last_detection[jersey_number] = 0
            
            # Update the athletes_data with the detected jersey numbers
            for track_id, jersey_number in self.jersey_map.items():
                if jersey_number in athletes_data:
                    # Update the track_id for this jersey number
                    athletes_data[jersey_number]['track_id'] = track_id
                    
                    # Update the detection confidence
                    athletes_data[jersey_number]['detection_confidence'] = self.confidence_map[track_id]
                    
                    # Mark as detected in this frame
                    athletes_data[jersey_number]['last_detected_frame'] = self.frame_count
                    
                    # Reset frames since last detection
                    self.frames_since_last_detection[jersey_number] = 0
            
            # Check for jerseys that haven't been detected for a while
            for jersey, frames in self.frames_since_last_detection.items():
                if frames > self.max_frames_to_keep_association and jersey in athletes_data:
                    # Don't reset track IDs for stable associations
                    track_id = athletes_data[jersey].get('track_id')
                    if track_id is not None:
                        is_stable = any(tid for tid, jn in self.stable_associations.items() if jn == jersey)
                        if not is_stable:
                            print(f"Jersey {jersey} not detected for {frames} frames, but keeping association due to stability")
            
            # Store the jersey map for future frames
            athletes_data['_jersey_map'] = self.jersey_map
            athletes_data['_frame_count'] = self.frame_count
            
            return detected_jerseys
            
        except Exception as e:
            print(f"Error in jersey number detection: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_unidentified_athletes(self, athletes_data):
        """
        Get a list of unidentified athletes (track IDs without jersey numbers).
        
        Args:
            athletes_data: Dictionary of athlete data
            
        Returns:
            List of unidentified athletes
        """
        unidentified_athletes = []
        
        try:
            # Get all track IDs from the tracking process
            all_track_ids = set(self.jersey_map.keys())
            
            # Get track IDs that were matched to athletes
            matched_track_ids = set()
            for jersey_number, athlete in athletes_data.items():
                if isinstance(jersey_number, str) and jersey_number.isdigit() and jersey_number not in ['_jersey_map', '_frame_count']:
                    if athlete.get('track_id') is not None:
                        matched_track_ids.add(athlete['track_id'])
            
            # Find unidentified track IDs
            unidentified_track_ids = all_track_ids - matched_track_ids
            
            # Create unidentified athletes list
            for track_id in unidentified_track_ids:
                # Get the jersey number that was detected for this track_id
                detected_jersey = self.jersey_map.get(track_id, '')
                
                # Only add if we actually detected a jersey number
                if detected_jersey:
                    unidentified_athletes.append({
                        'id': f"unidentified_{track_id}",
                        'track_id': track_id,
                        'detected_jersey': detected_jersey,
                        'confidence': self.confidence_map.get(track_id, 0.5)
                    })
            
            return unidentified_athletes
            
        except Exception as e:
            print(f"Error getting unidentified athletes: {e}")
            traceback.print_exc()
            return []
    
    def get_detected_athletes(self, athletes_data):
        """
        Get a dictionary of detected athletes with their jersey numbers.
        
        Args:
            athletes_data: Dictionary of athlete data
            
        Returns:
            Dictionary of detected athletes
        """
        detected_athletes = {}
        
        try:
            for jersey_number, athlete in athletes_data.items():
                if isinstance(jersey_number, str) and jersey_number.isdigit() and jersey_number not in ['_jersey_map', '_frame_count']:
                    if athlete.get('track_id') is not None:
                        # This athlete was detected
                        detected_athletes[jersey_number] = {
                            'id': athlete['id'],
                            'name': athlete['name'],
                            'jersey_number': jersey_number,
                            'track_id': athlete['track_id'],
                            'detection_confidence': athlete.get('detection_confidence', 0.0),
                            'last_detected_frame': athlete.get('last_detected_frame', 0),
                            'detected_jersey': jersey_number
                        }
            
            return detected_athletes
            
        except Exception as e:
            print(f"Error getting detected athletes: {e}")
            traceback.print_exc()
            return {} 