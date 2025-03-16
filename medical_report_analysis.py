import os
import json
import numpy as np
from PIL import Image
import fitz  # PyMuPDF
import torch
from transformers import pipeline
from mistral_analysis_service import MistralAnalysisService
import firebase_admin
from firebase_admin import credentials, firestore, storage
import cv2
import pdfplumber
import spacy
import re
from datetime import datetime
import traceback
from typing import List, Dict, Any, Optional
from google.cloud.firestore import SERVER_TIMESTAMP
import tempfile

class MedicalReportAnalysis:
    def __init__(self):
        """Initialize the medical report analysis service."""
        print("Initializing Medical Report Analysis service...")
        self.mistral_service = MistralAnalysisService()
        try:
            # Use PyTorch version instead of TensorFlow for summarization
            self.summarizer = pipeline("summarization", model="facebook/bart-large-cnn", framework="pt")
            print("Summarization model loaded successfully!")
        except Exception as e:
            print(f"Error loading summarization model: {e}")
            print("Using fallback summarization method")
            self.summarizer = None
        
        try:
            import spacy
            self.nlp = spacy.load('en_core_web_sm')
        except:
            import en_core_web_sm
            self.nlp = en_core_web_sm.load()
        print("NLP model loaded successfully")
        
        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate("serviceAccountKey.json")
                firebase_admin.initialize_app(cred)
            self.db = firestore.client()
            print("Firebase initialized successfully")
        except Exception as e:
            print(f"Error initializing Firebase: {e}")
            raise

    def extract_text_from_pdf(self, pdf_path):
        """Extract text and tables from PDF medical reports with enhanced HTML support."""
        text_content = []
        tables = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    # Extract text
                    text = page.extract_text()
                    if text:
                        text_content.append(text)
                    
                    # Extract tables with improved HTML table handling
                    page_tables = page.extract_tables()
                    if page_tables:
                        for table in page_tables:
                            # Convert table to text format
                            table_text = '\n'.join([
                                ' | '.join([str(cell).strip() if cell is not None else '' for cell in row])
                                for row in table if any(cell is not None for cell in row)
                            ])
                            if 'Body Part' in table_text or 'Injury Type' in table_text:
                                text_content.append(table_text)
                                tables.extend(page_tables)
                    
                    # Additional HTML table extraction
                    html_tables = re.findall(r'<table[^>]*>(.*?)</table>', text, re.DOTALL | re.IGNORECASE)
                    for html_table in html_tables:
                        # Extract rows from HTML table
                        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html_table, re.DOTALL | re.IGNORECASE)
                        table_data = []
                        for row in rows:
                            # Extract cells (both th and td)
                            cells = re.findall(r'<t[hd][^>]*>(.*?)</t[hd]>', row, re.DOTALL | re.IGNORECASE)
                            if cells:
                                table_data.append(cells)
                        
                        if table_data:
                            # Convert HTML table to text format
                            table_text = '\n'.join([' | '.join(row) for row in table_data])
                            if 'Body Part' in table_text or 'Injury Type' in table_text:
                                text_content.append(table_text)
                                tables.append(table_data)
            
            return "\n".join(text_content), tables
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            return "", []

    def analyze_injury_locations(self, pdf_path):
        """Extract injury locations and details from PDF."""
        injuries = []
        
        try:
            # Extract text from PDF
            text_content, tables = self.extract_text_from_pdf(pdf_path)
            print(f"Extracted text content (first 500 chars): {text_content[:500]}")
            
            # Process text content line by line
            lines = text_content.split('\n')
            current_section = None
            current_injury = {}
            
            # First pass: look for section headers to determine injury status
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Detect section headers
                line_lower = line.lower()
                if any(header in line_lower for header in ['current active injuries', 'recent past injuries', 'recovered injuries', 'injury assessment']):
                    if 'active' in line_lower:
                        current_section = 'active'
                    elif 'past' in line_lower:
                        current_section = 'past'
                    elif 'recovered' in line_lower:
                        current_section = 'recovered'
                    elif 'assessment' in line_lower:
                        current_section = 'active'  # Default to active for "Injury Assessment" section
                    continue
            
            # If no section was found, default to active
            if not current_section:
                current_section = 'active'
            
            # Second pass: extract injury details
            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                
                line_lower = line.lower()
                
                # Check for injury status in the line itself
                if 'active' in line_lower and not current_injury:
                    current_section = 'active'
                elif 'past' in line_lower and not current_injury:
                    current_section = 'past'
                elif 'recovered' in line_lower and not current_injury:
                    current_section = 'recovered'
                
                # Format 1: "Location: Right Hamstring"
                if 'location:' in line_lower:
                    if current_injury and 'bodyPart' in current_injury:
                        injuries.append(current_injury)
                        current_injury = {}
                    location = line.split('Location:')[1].strip()
                    side = 'right' if 'right' in location.lower() else 'left' if 'left' in location.lower() else 'center'
                    body_part = location.replace('Right', '').replace('Left', '').strip()
                    current_injury = {
                        'bodyPart': body_part,
                        'side': side,
                        'status': current_section
                    }
                
                # Format 2: "Body Part: Hamstring Side: Left"
                elif 'body part:' in line_lower:
                    if current_injury and 'bodyPart' in current_injury:
                        injuries.append(current_injury)
                        current_injury = {}
                    
                    # Extract body part
                    body_part_match = re.search(r'body part:\s*([^:]+)', line_lower, re.IGNORECASE)
                    if body_part_match:
                        body_part = body_part_match.group(1).strip()
                        current_injury['bodyPart'] = body_part
                    
                    # Check if side is in the same line
                    side_match = re.search(r'side:\s*([^:]+)', line_lower, re.IGNORECASE)
                    if side_match:
                        side = side_match.group(1).strip().lower()
                        current_injury['side'] = side
                    else:
                        # Check next line for side
                        if i + 1 < len(lines) and 'side:' in lines[i+1].lower():
                            side = lines[i+1].split('Side:')[1].strip().lower()
                            current_injury['side'] = side
                    
                    # Set status
                    current_injury['status'] = current_section
                
                # Handle side if it's on a separate line
                elif 'side:' in line_lower and current_injury and 'side' not in current_injury:
                    side = line.split('Side:')[1].strip().lower()
                    current_injury['side'] = side
                
                # Handle severity
                elif 'severity:' in line_lower and current_injury:
                    severity = line.split('Severity:')[1].strip().lower()
                    current_injury['severity'] = severity
                
                # Handle injury type
                elif 'type:' in line_lower and current_injury:
                    current_injury['injuryType'] = line.split('Type:')[1].strip()
                
                # Handle description/notes
                elif ('notes:' in line_lower or 'description:' in line_lower) and current_injury:
                    if 'notes:' in line_lower:
                        current_injury['description'] = line.split('Notes:')[1].strip()
                    else:
                        current_injury['description'] = line.split('Description:')[1].strip()
                    
                    # Complete the injury record
                    if 'severity' not in current_injury:
                        current_injury['severity'] = 'moderate'  # Default severity
                    
                    current_injury['colorCode'] = self._get_injury_color(current_section, current_injury.get('severity', 'moderate'))
                    current_injury['recoveryProgress'] = self._calculate_recovery_progress(current_section)
                    current_injury['lastUpdated'] = datetime.now().isoformat()
                    
                    # Add the injury if it has the minimum required fields
                    if 'bodyPart' in current_injury:
                        injuries.append(current_injury)
                        current_injury = {}
            
            # Add the last injury if not already added
            if current_injury and 'bodyPart' in current_injury:
                # Set default values for required fields
                if 'severity' not in current_injury:
                    current_injury['severity'] = 'moderate'
                if 'side' not in current_injury:
                    current_injury['side'] = 'center'
                
                current_injury['colorCode'] = self._get_injury_color(current_section, current_injury.get('severity', 'moderate'))
                current_injury['recoveryProgress'] = self._calculate_recovery_progress(current_section)
                current_injury['lastUpdated'] = datetime.now().isoformat()
                
                injuries.append(current_injury)
            
            # If no injuries were found using the structured approach, try a more flexible approach
            if not injuries:
                print("No structured injuries found, trying flexible extraction...")
                injuries = self._extract_injuries_flexible(text_content)
            
            print(f"Total injuries found: {len(injuries)}")
            for injury in injuries:
                print(f"Found injury: {injury}")
            
            return injuries
            
        except Exception as e:
            print(f"Error analyzing injury locations: {e}")
            traceback.print_exc()
            return []

    def _extract_injuries_flexible(self, text_content):
        """Extract injuries using a more flexible approach for less structured documents."""
        injuries = []
        
        # Look for common patterns indicating injuries
        body_part_patterns = [
            r'(hamstring|quadriceps|biceps|triceps|shoulder|knee|ankle|hip|elbow|wrist|calf|thigh|arm|leg|foot|hand|neck|back|chest|abdomen)',
            r'body\s*part[:\s]+([a-zA-Z]+)',
            r'injury\s*to\s*([a-zA-Z]+)',
            r'([a-zA-Z]+)\s*strain',
            r'([a-zA-Z]+)\s*sprain',
            r'([a-zA-Z]+)\s*tear',
            r'([a-zA-Z]+)\s*injury'
        ]
        
        # Improved side patterns to better separate from body part
        side_patterns = [
            r'\b(left|right|bilateral)\b',
            r'side[:\s]+(left|right|bilateral)',
        ]
        
        severity_patterns = [
            r'(mild|moderate|severe)',
            r'severity[:\s]+(mild|moderate|severe)',
            r'grade\s*([1-3])',
        ]
        
        status_patterns = [
            r'(active|recovering|recovered|past)',
            r'status[:\s]+(active|recovering|recovered|past)',
        ]
        
        # Find all potential body parts
        body_parts = []
        for pattern in body_part_patterns:
            matches = re.finditer(pattern, text_content.lower())
            for match in matches:
                # Clean up the body part name - remove "side" if it's attached
                body_part = match.group(1).strip()
                if body_part.endswith(' side'):
                    body_part = body_part[:-5].strip()
                
                body_parts.append((body_part, match.start()))
        
        # For each body part, try to find associated side, severity, and status
        for body_part, position in body_parts:
            # Look for context in a window around the body part mention
            context_start = max(0, position - 100)
            context_end = min(len(text_content), position + 100)
            context = text_content[context_start:context_end].lower()
            
            # Find side
            side = 'center'
            for pattern in side_patterns:
                side_match = re.search(pattern, context)
                if side_match:
                    side_group = 1
                    if 'side' in pattern:
                        side_group = 1
                    side = side_match.group(side_group).lower()
                    break
            
            # Find severity
            severity = 'moderate'
            for pattern in severity_patterns:
                severity_match = re.search(pattern, context)
                if severity_match:
                    severity_value = severity_match.group(1).lower()
                    # Convert grade to severity
                    if severity_value == '1':
                        severity = 'mild'
                    elif severity_value == '2':
                        severity = 'moderate'
                    elif severity_value == '3':
                        severity = 'severe'
                    else:
                        severity = severity_value
                    break
            
            # Find status
            status = 'active'
            for pattern in status_patterns:
                status_match = re.search(pattern, context)
                if status_match:
                    status = status_match.group(1).lower()
                    break
            
            # Create injury record
            injury = {
                'bodyPart': body_part,
                'side': side,
                'status': status,
                'severity': severity,
                'colorCode': self._get_injury_color(status, severity),
                'recoveryProgress': self._calculate_recovery_progress(status),
                'lastUpdated': datetime.now().isoformat()
            }
            
            # Check if this is a duplicate
            is_duplicate = False
            for existing_injury in injuries:
                if existing_injury['bodyPart'] == injury['bodyPart'] and existing_injury['side'] == injury['side']:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                injuries.append(injury)
        
        return injuries

    def _map_body_part(self, text):
        """Map various body part descriptions to standardized format."""
        text = text.lower().strip()
        
        # Remove "side" if it's part of the body part name
        if text.endswith(' side'):
            text = text[:-5].strip()
        
        # Direct mappings
        mappings = {
            'head': 'head',
            'neck': 'neck',
            'shoulder': 'shoulder',
            'upper arm': 'upper_arm',
            'elbow': 'elbow',
            'forearm': 'forearm',
            'wrist': 'wrist',
            'hand': 'hand',
            'chest': 'chest',
            'upper back': 'upper_back',
            'lower back': 'lower_back',
            'lumbar': 'lower_back',
            'thoracic': 'upper_back',
            'hip': 'hip',
            'thigh': 'thigh',
            'hamstring': 'thigh',
            'quadriceps': 'thigh',
            'knee': 'knee',
            'shin': 'shin',
            'calf': 'shin',
            'ankle': 'ankle',
            'foot': 'foot',
            # Add more specific mappings for ankle and knee
            'ankle joint': 'ankle',
            'talocrural': 'ankle',
            'talus': 'ankle',
            'calcaneus': 'ankle',
            'knee joint': 'knee',
            'patella': 'knee',
            'patellar': 'knee',
            'tibiofemoral': 'knee',
            'meniscus': 'knee'
        }
        
        # Check direct mappings
        for key, value in mappings.items():
            if key in text:
                return value
        
        # Handle special cases
        if 'back' in text:
            if 'upper' in text or 'thoracic' in text:
                return 'upper_back'
            if 'lower' in text or 'lumbar' in text:
                return 'lower_back'
            return 'back'
        
        if 'arm' in text:
            if 'upper' in text:
                return 'upper_arm'
            if 'fore' in text:
                return 'forearm'
            return 'arm'
        
        if 'leg' in text:
            if 'upper' in text or 'thigh' in text:
                return 'thigh'
            if 'lower' in text or 'shin' in text:
                return 'shin'
            return 'leg'
        
        return None

    def _determine_severity(self, injury_type, status):
        """Determine injury severity based on type and status."""
        injury_type = injury_type.lower()
        
        severe_indicators = ['severe', 'fracture', 'rupture', 'tear', 'broken']
        moderate_indicators = ['moderate', 'sprain', 'strain', 'inflammation']
        mild_indicators = ['mild', 'contusion', 'bruise', 'soreness']
        
        if any(indicator in injury_type for indicator in severe_indicators):
            return 'severe'
        if any(indicator in injury_type for indicator in moderate_indicators):
            return 'moderate'
        if any(indicator in injury_type for indicator in mild_indicators):
            return 'mild'
        
        # Default based on status
        if status == 'recovered':
            return 'mild'
        if status == 'recovering':
            return 'moderate'
        return 'moderate'  # Default severity

    def _determine_side(self, text):
        """Determine which side (left/right) the injury is on."""
        text = text.lower()
        if 'bilateral' in text or 'both sides' in text:
            return 'bilateral'
        elif 'right' in text:
            return 'right'
        elif 'left' in text:
            return 'left'
        return 'center'

    def _determine_injury_status(self, text):
        """Determine injury status based on context."""
        text = text.lower()
        if any(word in text for word in ['healed', 'recovered', 'resolved', 'normal', 'cleared']):
            return 'recovered'
        elif any(word in text for word in ['healing', 'improving', 'rehabilitating', 'progress', 'better']):
            return 'recovering'
        return 'active'

    def _calculate_recovery_progress(self, status):
        """Calculate recovery progress percentage based on status."""
        if status == 'active':
            return 0
        elif status == 'past':
            return 50
        else:  # recovered
            return 100

    def _get_3d_coordinates(self, body_part, side):
        """Get precise 3D coordinates for the body part."""
        base_coords = {
            'head': {'x': 0, 'y': 1.8, 'z': 0},
            'neck': {'x': 0, 'y': 1.65, 'z': 0},
            'shoulder': {'x': 0.2, 'y': 1.5, 'z': 0},
            'upper_arm': {'x': 0.25, 'y': 1.35, 'z': 0},
            'elbow': {'x': 0.3, 'y': 1.2, 'z': 0},
            'forearm': {'x': 0.28, 'y': 1.1, 'z': 0},
            'wrist': {'x': 0.25, 'y': 1.0, 'z': 0},
            'hand': {'x': 0.3, 'y': 0.9, 'z': 0},
            'chest': {'x': 0, 'y': 1.4, 'z': 0.1},
            'upper_back': {'x': 0, 'y': 1.4, 'z': -0.1},
            'lower_back': {'x': 0, 'y': 1.2, 'z': -0.1},
            'hip': {'x': 0.15, 'y': 1.1, 'z': 0},
            'thigh': {'x': 0.18, 'y': 0.9, 'z': 0},
            'knee': {'x': 0.18, 'y': 0.6, 'z': 0},
            'shin': {'x': 0.17, 'y': 0.4, 'z': 0},
            'ankle': {'x': 0.15, 'y': 0.2, 'z': 0},
            'foot': {'x': 0.15, 'y': 0.1, 'z': 0}
        }
        
        coords = base_coords.get(body_part, {'x': 0, 'y': 1.0, 'z': 0}).copy()
        
        # Adjust x-coordinate based on side
        if side == 'left':
            coords['x'] = -abs(coords['x'])
        elif side == 'right':
            coords['x'] = abs(coords['x'])
        elif side == 'bilateral':
            # Create two entries for bilateral injuries
            return [
                {**coords, 'x': abs(coords['x'])},
                {**coords, 'x': -abs(coords['x'])}
            ]
        
        return coords

    def _get_injury_color(self, status, severity):
        """Get color code based on injury status and severity."""
        if status == 'active':
            if severity == 'severe':
                return '#FF0000'  # Bright red
            elif severity == 'moderate':
                return '#FF4444'  # Medium red
            else:
                return '#FF8888'  # Light red
        elif status == 'past':
            if severity == 'severe':
                return '#FFA500'  # Orange
            elif severity == 'moderate':
                return '#FFB52E'  # Light orange
            else:
                return '#FFC966'  # Very light orange
        else:  # recovered
            if severity == 'severe':
                return '#228B22'  # Forest green
            elif severity == 'moderate':
                return '#32CD32'  # Lime green
            else:
                return '#90EE90'  # Light green

    async def process_medical_report(self, pdf_path, athlete_id, title, diagnosis):
        """Process a medical report PDF and store results."""
        try:
            # Extract text from PDF
            text_content, tables = self.extract_text_from_pdf(pdf_path)
            print("Extracted text content length:", len(text_content))  # Debug log
            
            # Check if content is HTML
            if '<html' in text_content.lower():
                print("Detected HTML content")  # Debug log
                # Extract the body content
                body_match = re.search(r'<body[^>]*>(.*?)</body>', text_content, re.DOTALL | re.IGNORECASE)
                if body_match:
                    text_content = body_match.group(1)
                    print("Extracted body content length:", len(text_content))  # Debug log
            
            # Analyze injury locations and details
            injury_analysis = self.analyze_injury_locations(pdf_path)
            print(f"Found {len(injury_analysis)} injuries:")  # Debug log
            for injury in injury_analysis:
                print(f"- {injury['bodyPart']} ({injury['side']}): {injury['injuryType']} - {injury['status']}")
            
            # Extract patient information
            patient_info = {}
            patient_match = re.search(r'<div[^>]*class="patient-info"[^>]*>(.*?)</div>', text_content, re.DOTALL | re.IGNORECASE)
            if patient_match:
                info_text = patient_match.group(1)
                # Extract name
                name_match = re.search(r'Name:.*?([^<\n]+)', info_text)
                if name_match:
                    patient_info['name'] = name_match.group(1).strip()
                # Extract other fields similarly
            
            # Generate summary
            if len(text_content) > 1024:
                summary_text = text_content[:1024]
            else:
                summary_text = text_content
            summary = self.summarizer(summary_text, max_length=130, min_length=30)[0]['summary_text']
            
            # Store results in Firestore
            report_data = {
                'athlete_id': athlete_id,
                'title': title or "Medical Assessment Report",
                'diagnosis': diagnosis or "Injury Assessment",
                'timestamp': datetime.now(),
                'injuries': injury_analysis,
                'summary': summary,
                'patient_info': patient_info,
                'status': 'processed'
            }
            
            # Add to Firestore
            report_ref = self.db.collection('medical_reports').document()
            await report_ref.set(report_data)
            
            print(f"Stored medical report with ID: {report_ref.id}")
            print(f"Report data: {json.dumps(report_data, indent=2)}")  # Debug log
            
            return {
                'status': 'success',
                'report_id': report_ref.id,
                'title': report_data['title'],
                'diagnosis': report_data['diagnosis'],
                'summary': summary,
                'injuries': injury_analysis,
                'patient_info': patient_info
            }
            
        except Exception as e:
            print(f"Error processing medical report: {str(e)}")
            traceback.print_exc()
            return {
                'status': 'error',
                'message': str(e)
            }

    async def get_athlete_report_history(self, athlete_id):
        """Retrieve the medical report history for an athlete."""
        try:
            print(f"Querying Firestore for athlete: {athlete_id}")
            # Query Firestore for reports
            reports_ref = self.db.collection('medical_reports')\
                .where('athlete_id', '==', athlete_id)\
                .order_by('timestamp', direction=firestore.Query.DESCENDING)
            
            # Get the documents
            reports = reports_ref.get()
            
            # Convert to list and process timestamps
            report_list = []
            for doc in reports:
                report_data = doc.to_dict()
                report_data['id'] = doc.id
                
                # Convert timestamp to string
                if 'timestamp' in report_data:
                    if isinstance(report_data['timestamp'], datetime):
                        report_data['timestamp'] = report_data['timestamp'].isoformat()
                    elif isinstance(report_data['timestamp'], firestore.SERVER_TIMESTAMP):
                        report_data['timestamp'] = datetime.now().isoformat()
                
                # Process injuries
                if 'injuries' in report_data:
                    injuries = report_data['injuries']
                    if isinstance(injuries, list):
                        for injury in injuries:
                            if isinstance(injury, dict) and 'lastUpdated' in injury:
                                if isinstance(injury['lastUpdated'], datetime):
                                    injury['lastUpdated'] = injury['lastUpdated'].isoformat()
                                elif isinstance(injury['lastUpdated'], str):
                                    # Verify it's a valid ISO format
                                    try:
                                        datetime.fromisoformat(injury['lastUpdated'].replace('Z', '+00:00'))
                                    except ValueError:
                                        injury['lastUpdated'] = datetime.now().isoformat()
                
                report_list.append(report_data)
            
            print(f"Retrieved {len(report_list)} reports for athlete {athlete_id}")
            for report in report_list:
                print(f"Report ID: {report.get('id')}")
                print(f"Title: {report.get('title')}")
                injuries = report.get('injuries', [])
                print(f"Injuries: {len(injuries)}")
                if injuries:
                    print("Injury details:")
                    for injury in injuries:
                        print(f"- {injury.get('bodyPart')} ({injury.get('side')}): {injury.get('injuryType')} - {injury.get('status')}")
            
            return report_list
            
        except Exception as e:
            print(f"Error retrieving medical reports: {e}")
            traceback.print_exc()
            return [] 