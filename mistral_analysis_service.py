import numpy as np
from typing import Dict, List, Any
import json
import os
import requests
import re  # Add import for regex

# Try to import transformers and torch, but make them optional
try:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    print("WARNING: Transformers or PyTorch not available. MistralAnalysisService will use API-only mode.")
    TRANSFORMERS_AVAILABLE = False

class MistralAnalysisService:
    def __init__(self):
        # Get API key from environment variables
        self.api_key = os.getenv('MISTRAL_API_KEY', '')
        self.api_url = "https://api.mistral.ai/v1/chat/completions"
        self.using_api = self.api_key != ''
        
        # Sport-specific prompts
        self.sport_prompts = {
            "weightlifting": "Analyze weightlifting performance focusing on form, balance, and symmetry metrics:",
            "swimming": "Analyze swimming performance focusing on movement smoothness and body coordination:",
            "running": "Analyze running performance focusing on gait, symmetry, and movement efficiency:"
        }

        # Anatomical mappings
        self.anatomical_mappings = {
            'biceps brachii': ['Biceps_Brachii', 'Bicep', 'biceps.l', 'biceps.r'],
            'triceps brachii': ['Triceps_Brachii', 'Tricep', 'triceps.l', 'triceps.r'],
            'deltoid': ['Deltoid', 'deltoideus', 'deltoid.l', 'deltoid.r'],
            'gastrocnemius': ['Gastrocnemius', 'Calf_Muscle', 'gastrocnemius.l', 'gastrocnemius.r'],
            'quadriceps': ['Femoris', 'Quad', 'quadriceps.l', 'quadriceps.r'],
            'trapezius': ['Trapezius', 'Trap', 'trapezius.l', 'trapezius.r'],
            'latissimus dorsi': ['Latissimus_Dorsi', 'Lat', 'latissimus.l', 'latissimus.r'],
            'pectoralis major': ['Pectoralis_Major', 'Chest', 'pectoralis.l', 'pectoralis.r'],
            'rectus abdominis': ['Rectus_Abdominis', 'Abs', 'abdominals'],
            'gluteus maximus': ['Gluteus_Maximus', 'Glute', 'gluteus.l', 'gluteus.r']
        }

        # Only load the model if transformers is available and we don't have an API key
        if TRANSFORMERS_AVAILABLE and not self.using_api:
            try:
                # Initialize with a publicly available model
                self.model_name = "facebook/opt-350m"
                print(f"Loading model {self.model_name}...")
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    torch_dtype=torch.float16,
                    device_map="auto"
                )
                print("Model loaded successfully!")
            except Exception as e:
                print(f"Error loading model: {e}")
                self.model = None
                self.tokenizer = None
        else:
            self.model = None
            self.tokenizer = None
            if self.using_api:
                print("Using Mistral API for analysis")
            else:
                print("No transformers available and no API key - will use fallback methods")

    def generate_analysis(self, metrics: Dict[str, float], sport_type: str, historical_data: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate detailed performance analysis using Mistral.
        
        Args:
            metrics: Current performance metrics
            sport_type: Type of sport being analyzed
            historical_data: Optional historical performance data
        
        Returns:
            Dictionary containing analysis and recommendations
        """
        # Prepare the context with metrics
        metrics_str = json.dumps(metrics, indent=2)
        historical_context = self._prepare_historical_context(historical_data) if historical_data else ""
        
        # Create the prompt
        prompt = f"""<s>[INST] You are a professional sports performance analyst. Analyze these {sport_type} performance metrics and provide detailed insights:

Current Performance Metrics:
{metrics_str}

{historical_context}

Provide analysis in the following format:
1. Overall Performance Assessment
2. Key Strengths
3. Areas for Improvement
4. Specific Recommendations
5. Training Focus Points [/INST]"""

        # Try API first if available
        if self.using_api:
            analysis_text = self._call_mistral(prompt)
            if analysis_text:
                return self._parse_analysis(analysis_text)

        # Use local model if available
        if self.model and self.tokenizer:
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
            outputs = self.model.generate(
                inputs["input_ids"],
                max_length=1000,
                temperature=0.7,
                top_p=0.95,
                do_sample=True,
                num_return_sequences=1
            )
            
            analysis_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            return self._parse_analysis(analysis_text)
        
        # Fallback method if neither API nor model is available
        return self._generate_fallback_analysis(metrics, sport_type)
    
    def _generate_fallback_analysis(self, metrics: Dict[str, float], sport_type: str) -> Dict[str, Any]:
        """Generate a simple fallback analysis when no model is available."""
        # Basic analysis based on metrics
        strengths = []
        improvements = []
        
        # Analyze each metric
        for name, value in metrics.items():
            if value > 0.7:  # Arbitrary threshold
                strengths.append(f"High {name}: {value:.2f}")
            elif value < 0.3:  # Arbitrary threshold
                improvements.append(f"Low {name}: {value:.2f}")
        
        return {
            "overall_assessment": f"Basic {sport_type} performance analysis based on provided metrics.",
            "key_strengths": strengths[:3],  # Top 3 strengths
            "areas_for_improvement": improvements[:3],  # Top 3 improvements
            "recommendations": ["Maintain regular training schedule", 
                               "Focus on areas with lower scores",
                               "Consider professional coaching for specific techniques"],
            "training_focus": ["General conditioning", 
                              "Technique refinement",
                              "Recovery management"]
        }

    def generate_real_time_feedback(self, current_metrics: Dict[str, float], sport_type: str) -> str:
        """
        Generate real-time feedback during performance.
        
        Args:
            current_metrics: Current frame's performance metrics
            sport_type: Type of sport
        
        Returns:
            String containing immediate feedback
        """
        metrics_str = json.dumps(current_metrics, indent=2)
        prompt = f"""<s>[INST] As a {sport_type} coach, provide brief, actionable real-time feedback based on these metrics:

{metrics_str}

Provide a single, specific instruction for improvement. [/INST]"""

        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        outputs = self.model.generate(
            inputs["input_ids"],
            max_length=100,
            temperature=0.3,
            top_p=0.95,
            do_sample=True,
            num_return_sequences=1
        )
        
        feedback = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        return feedback.strip()

    def _prepare_historical_context(self, historical_data: List[Dict[str, Any]]) -> str:
        """Prepare historical data context for analysis."""
        if not historical_data:
            return ""
            
        recent_trends = self._calculate_trends(historical_data)
        return f"""

Historical Performance Context:
{json.dumps(recent_trends, indent=2)}"""

    def _calculate_trends(self, historical_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate performance trends from historical data."""
        if not historical_data:
            return {}
            
        metrics = list(historical_data[0]["metrics"].keys())
        trends = {}
        
        for metric in metrics:
            values = [session["metrics"].get(metric, 0) for session in historical_data]
            trends[f"{metric}_trend"] = self._calculate_trend(values)
            
        return trends

    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate the trend line slope for a metric."""
        if not values:
            return 0.0
        x = np.arange(len(values))
        y = np.array(values)
        return np.polyfit(x, y, 1)[0] if len(values) > 1 else 0.0

    def _parse_analysis(self, analysis_text: str) -> Dict[str, Any]:
        """Parse the generated analysis into structured format."""
        sections = analysis_text.split("\n\n")
        analysis = {
            "overall_assessment": "",
            "key_strengths": [],
            "areas_for_improvement": [],
            "recommendations": [],
            "training_focus": []
        }
        
        current_section = None
        for section in sections:
            if "Overall Performance Assessment" in section:
                current_section = "overall_assessment"
            elif "Key Strengths" in section:
                current_section = "key_strengths"
            elif "Areas for Improvement" in section:
                current_section = "areas_for_improvement"
            elif "Specific Recommendations" in section:
                current_section = "recommendations"
            elif "Training Focus Points" in section:
                current_section = "training_focus"
            elif current_section:
                if current_section == "overall_assessment":
                    analysis[current_section] = section.strip()
                else:
                    points = [p.strip() for p in section.split("\n") if p.strip()]
                    analysis[current_section].extend(points)
                    
        return analysis 

    def _call_mistral(self, prompt: str) -> str:
        """Call the Mistral API with the given prompt."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "mistral-medium",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,  # Lower temperature for more precise answers
            "max_tokens": 800    # Increased for more detailed responses
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            print(f"Error calling Mistral AI: {e}")
            return ""

    def map_injury_to_mesh(self, injury: Dict[str, Any], available_meshes: List[str]) -> List[str]:
        """Map injury to relevant mesh names."""
        try:
            body_part = injury.get('bodyPart', '').lower()
            side = injury.get('side', '').lower()
            
            # Direct mapping using anatomical dictionary
            matching_meshes = []
            for anatomical_term, possible_meshes in self.anatomical_mappings.items():
                if anatomical_term in body_part:
                    for mesh_name in possible_meshes:
                        # Filter available meshes that match the anatomical term
                        matching = [m for m in available_meshes if mesh_name.lower() in m.lower()]
                        if matching:
                            # Apply side-specific filtering
                            if side == 'left':
                                side_meshes = [m for m in matching if '.l' in m.lower() or '_l_' in m.lower()]
                                matching_meshes.extend(side_meshes if side_meshes else matching)
                            elif side == 'right':
                                side_meshes = [m for m in matching if '.r' in m.lower() or '_r_' in m.lower()]
                                matching_meshes.extend(side_meshes if side_meshes else matching)
                            else:
                                matching_meshes.extend(matching)
            
            if matching_meshes:
                return list(set(matching_meshes))  # Remove duplicates
            
            # Fallback: Search for similar mesh names
            return [mesh for mesh in available_meshes 
                   if body_part in mesh.lower() 
                   and (side[0] if side else '') in mesh.lower()]
            
        except Exception as e:
            print(f"Error mapping injury to mesh: {str(e)}")
            return []
    
    def get_mesh_painting_instructions(self, target_meshes: List[str], injury: Dict[str, Any]) -> Dict[str, Any]:
        """Get painting instructions for the meshes."""
        try:
            status = injury.get('status', '').lower()
            severity = injury.get('severity', '').lower()
            
            # Color mapping
            color_map = {
                'active': (0.9, 0.1, 0.1, 1.0),    # Bright red
                'past': (0.9, 0.5, 0.1, 1.0),      # Bright orange
                'recovered': (0.1, 0.8, 0.1, 1.0),  # Bright green
                'default': (1.0, 0.0, 0.0, 1.0)    # Default red
            }
            
            # Alpha mapping
            alpha_map = {
                'mild': 0.4,
                'moderate': 0.6,
                'severe': 0.8,
                'default': 0.6
            }
            
            return {
                'meshes': target_meshes,
                'color': color_map.get(status, color_map['default']),
                'alpha': alpha_map.get(severity, alpha_map['default']),
                'emission': 0.2 if status == 'active' else 0.1
            }
            
        except Exception as e:
            print(f"Error getting painting instructions: {str(e)}")
            return {}

    def analyze_injury_description(self, injury_text: str) -> Dict[str, Any]:
        """Analyze injury description to extract structured data."""
        
        prompt = f"""Analyze this injury description and extract key information in a structured format:

{injury_text}

Extract and return:
1. Primary muscle/body part affected
2. Side (left, right, or bilateral)
3. Type of injury
4. Severity
5. Current status
6. Any specific anatomical details mentioned

Format the response as a structured list."""

        response = self._call_mistral(prompt)
        
        # Process the response into a structured format
        # (You can enhance this parsing based on the actual response format)
        return {
            'analysis': response,
            'structured_data': self._parse_analysis_response(response)
        }
    
    def _parse_analysis_response(self, response: str) -> Dict[str, Any]:
        """Parse the Mistral analysis response into structured data."""
        # Add parsing logic here
        return {
            'parsed': response
        }

    def analyze_muscle_relationships(self, context: str) -> Dict[str, Any]:
        """
        Analyze relationships between muscles and find similar or related muscles.
        
        Args:
            context: Detailed context about the target muscle and available meshes
            
        Returns:
            Dictionary containing analysis and suggestions
        """
        try:
            # If API key is available, use the Mistral API
            if self.api_key:
                print("Using Mistral API for muscle relationship analysis")
                response = self._call_mistral(context)
                
                # Extract suggestions from the response
                suggestions = []
                outer_meshes = []
                inner_meshes = []
                
                # Process the response to extract different types of mesh suggestions
                if response:
                    lines = response.split('\n')
                    current_section = None
                    
                    for line in lines:
                        line = line.strip()
                        
                        # Detect section headers
                        if "primary mesh suggestion" in line.lower() or "primary mesh" in line.lower():
                            current_section = "primary"
                            continue
                        elif "secondary mesh suggestion" in line.lower() or "secondary mesh" in line.lower():
                            current_section = "secondary"
                            continue
                        elif "outer visible mesh" in line.lower() or "superficial mesh" in line.lower():
                            current_section = "outer"
                            continue
                        elif "inner related mesh" in line.lower() or "deep muscle" in line.lower():
                            current_section = "inner"
                            continue
                        elif "explanation" in line.lower() or "reasoning" in line.lower():
                            current_section = "explanation"
                            continue
                        
                        # Skip empty lines or section headers
                        if not line or line.startswith('#') or line.startswith('*') or line.startswith('-'):
                            continue
                            
                        # Extract mesh names from the line
                        if current_section in ["primary", "secondary", "outer", "inner"]:
                            # Look for mesh names in the line
                            # Common patterns: numbered lists, bullet points, or plain text
                            mesh_name = None
                            
                            # Try to extract from numbered list (e.g., "1. MeshName")
                            if re.match(r'^\d+\.', line):
                                mesh_name = re.sub(r'^\d+\.\s*', '', line)
                            # Try to extract from bullet points (e.g., "- MeshName")
                            elif line.startswith('-') or line.startswith('*'):
                                mesh_name = re.sub(r'^[-*]\s*', '', line)
                            # Try to extract from plain text
                            else:
                                # If it contains a colon, take the part before the colon
                                if ':' in line:
                                    mesh_name = line.split(':', 1)[0].strip()
                                else:
                                    mesh_name = line
                            
                            # Clean up the mesh name
                            if mesh_name:
                                # Remove any trailing punctuation or explanations
                                mesh_name = re.sub(r'[,;:].*$', '', mesh_name).strip()
                                
                                # Add to the appropriate list
                                if current_section == "primary":
                                    suggestions.append(mesh_name)
                                elif current_section == "secondary":
                                    if mesh_name not in suggestions:
                                        suggestions.append(mesh_name)
                                elif current_section == "outer":
                                    if mesh_name not in outer_meshes:
                                        outer_meshes.append(mesh_name)
                                elif current_section == "inner":
                                    if mesh_name not in inner_meshes:
                                        inner_meshes.append(mesh_name)
                
                # If no structured sections were found, try a more general extraction
                if not suggestions:
                    # Look for any mesh-like terms in the response
                    words = re.findall(r'\b\w+\b', response)
                    for word in words:
                        if len(word) > 5 and any(term in word.lower() for term in ['muscle', 'tendon', 'ligament', 'bone']):
                            suggestions.append(word)
                
                return {
                    'suggestions': suggestions,
                    'outer_meshes': outer_meshes,
                    'inner_meshes': inner_meshes,
                    'full_response': response
                }
            
            # Fallback to local model if available
            if self.model and self.tokenizer and TRANSFORMERS_AVAILABLE:
                print("Using local model for muscle relationship analysis")
                inputs = self.tokenizer(context, return_tensors="pt").to(self.model.device)
                outputs = self.model.generate(
                    inputs["input_ids"],
                    max_length=800,  # Increased for more detailed response
                    temperature=0.3,
                    top_p=0.95,
                    do_sample=True,
                    num_return_sequences=1
                )
                
                analysis_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
                
                # Extract suggestions from the response
                suggestions = []
                lines = analysis_text.split('\n')
                for line in lines:
                    if ':' in line and any(word in line.lower() for word in ['suggest', 'recommend', 'mesh', 'muscle']):
                        parts = line.split(':')
                        if len(parts) > 1:
                            mesh_names = parts[1].strip().split(',')
                            suggestions.extend([name.strip() for name in mesh_names if name.strip()])
                
                return {
                    'suggestions': suggestions,
                    'full_response': analysis_text
                }
                
            # If neither API nor model is available, return a simple fallback
            print("No AI service available for muscle relationship analysis, using fallback")
            return {
                'suggestions': ['biceps', 'triceps', 'deltoid', 'pectoralis', 'latissimus'],
                'outer_meshes': ['biceps', 'triceps', 'deltoid'],
                'inner_meshes': ['pectoralis', 'latissimus'],
                'fallback': True
            }
        except Exception as e:
            print(f"Error analyzing muscle relationships: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'suggestions': [], 'error': str(e)} 