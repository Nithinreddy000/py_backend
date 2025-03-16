import os
import json
import requests
from typing import List, Dict, Any, Optional
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AnatomicalAIService:
    """
    Service that uses AI to improve the accuracy of mapping between body parts 
    mentioned in medical reports and actual mesh names in 3D models.
    """
    
    def __init__(self, api_key: Optional[str] = None, use_local_fallback: bool = True, api_type: str = "mistral"):
        """
        Initialize the AnatomicalAIService.
        
        Args:
            api_key: API key for AI service (Mistral or Gemini)
            use_local_fallback: Whether to use local fallback methods if AI fails
            api_type: Type of API to use ("mistral" or "gemini")
        """
        self.api_key = api_key
        self.use_local_fallback = use_local_fallback
        self.api_type = api_type.lower()
        
        # Load anatomical knowledge base
        self.anatomical_knowledge = self._load_anatomical_knowledge()
        
        # Initialize cache for mesh matches
        self.mesh_cache = {}
        
        print("AnatomicalAIService initialized")
        if self.api_key:
            # Mask the API key for security in logs
            masked_key = self.api_key[:4] + "..." + self.api_key[-4:] if len(self.api_key) > 8 else "***"
            print(f"Using {self.api_type.capitalize()} API for enhanced mesh detection (API Key: {masked_key})")
            
            # Check if we have the required packages
            if self.api_type == "gemini":
                try:
                    import google.generativeai
                    print("Google Generative AI package is installed")
                except ImportError:
                    print("WARNING: google-generativeai package is not installed. Please install it with: pip install google-generativeai")
                    self.api_key = None
        else:
            print("No API key provided, using local fallback methods only")
    
    def _load_anatomical_knowledge(self) -> Dict[str, Any]:
        """Load the anatomical knowledge base from file or create a default one."""
        try:
            knowledge_path = os.path.join(os.path.dirname(__file__), "anatomical_knowledge.json")
            if os.path.exists(knowledge_path):
                with open(knowledge_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load anatomical knowledge base: {e}")
        
        # Create default knowledge base
        return {
            "synonyms": {
                "biceps": ["biceps brachii", "arm muscle", "upper arm"],
                "quadriceps": ["quads", "thigh muscle", "quadriceps femoris"],
                "gastrocnemius": ["calf muscle", "gastroc"],
                # Add more synonyms as needed
            },
            "relationships": {
                "biceps": ["brachialis", "brachioradialis"],
                "quadriceps": ["vastus lateralis", "vastus medialis", "vastus intermedius", "rectus femoris"],
                # Add more relationships as needed
            },
            "embeddings": {}  # Will be populated as we go
        }
    
    def _save_anatomical_knowledge(self):
        """Save the anatomical knowledge base to file."""
        try:
            knowledge_path = os.path.join(os.path.dirname(__file__), "anatomical_knowledge.json")
            with open(knowledge_path, 'w') as f:
                json.dump(self.anatomical_knowledge, f, indent=2)
            logger.info("Anatomical knowledge base saved")
        except Exception as e:
            logger.warning(f"Could not save anatomical knowledge base: {e}")
    
    def find_matching_meshes(self, body_part: str, available_meshes: List[str], 
                            side: Optional[str] = None) -> List[str]:
        """
        Find meshes that match a body part.
        
        Args:
            body_part: The body part to find meshes for
            available_meshes: List of available mesh names
            side: Optional side specification (left or right)
            
        Returns:
            List of matching mesh names
        """
        # Clean up body part name
        body_part = body_part.lower().strip()
        
        # Remove "side" if it's attached to the body part
        if body_part.endswith(" side"):
            body_part = body_part[:-5].strip()
        
        # Check cache first
        cache_key = f"{body_part}_{side if side else 'none'}"
        if cache_key in self.mesh_cache:
            print(f"Using cached matches for {body_part}")
            return self.mesh_cache[cache_key]
        
        # Special handling for foot-related terms
        if any(term in body_part for term in ['foot', 'ankle', 'plantar', 'calcaneus', 'metatarsal', 'tarsal']):
            print(f"SPECIAL HANDLING: '{body_part}' is foot-related, using aggressive matching")
            matches = self._aggressive_matching(body_part, available_meshes, side)
            if matches:
                self.mesh_cache[cache_key] = matches
                return matches
        
        # Try AI-based matching first if API key is available
        if self.api_key:
            print(f"Attempting AI-based matching for '{body_part}'")
            
            # Use the appropriate API based on the api_type
            if self.api_type == "gemini":
                # Try Gemini API first
                prompt = self._create_ai_prompt(body_part, available_meshes, side)
                matches = self._gemini_based_matching(prompt, available_meshes)
                if matches:
                    print(f"AI improved body part recognition: '{body_part} {side if side else ''}' -> '{body_part}'")
                    self.mesh_cache[cache_key] = matches
                    return matches
            else:
                # Try Mistral API
                prompt = self._create_ai_prompt(body_part, available_meshes, side)
                matches = self._mistral_based_matching(prompt, available_meshes)
                if matches:
                    print(f"AI improved body part recognition: '{body_part} {side if side else ''}' -> '{body_part}'")
                    self.mesh_cache[cache_key] = matches
                    return matches
        
        # If AI-based matching fails or no API key, try local fallback
        if self.use_local_fallback:
            print(f"Attempting local fallback matching for '{body_part}'")
            matches = self._local_fallback_matching(body_part, available_meshes, side)
            if matches:
                print(f"AI improved body part recognition: '{body_part} {side if side else ''}' -> '{body_part}'")
                self.mesh_cache[cache_key] = matches
                return matches
        
        # If all else fails, try aggressive matching
        print(f"Attempting aggressive matching for '{body_part}'")
        matches = self._aggressive_matching(body_part, available_meshes, side)
        if matches:
            print(f"AI improved body part recognition: '{body_part} {side if side else ''}' -> '{body_part}'")
            self.mesh_cache[cache_key] = matches
            return matches
            
        # If still no matches, try to get default meshes
        print(f"Attempting to get default meshes for '{body_part}'")
        matches = self._get_default_meshes(body_part, available_meshes, side)
        if matches:
            print(f"Using default meshes for '{body_part}'")
            self.mesh_cache[cache_key] = matches
            return matches
        
        print(f"No matches found for '{body_part}' after trying all methods")
        return []
    
    def _ai_based_matching(self, body_part: str, available_meshes: List[str], 
                          side: Optional[str] = None) -> List[str]:
        """
        Use AI to find the best matching meshes for a body part.
        
        Args:
            body_part: The body part to find meshes for
            available_meshes: List of available mesh names
            side: Optional side specification (left or right)
            
        Returns:
            List of matching mesh names
        """
        if not self.api_key:
            print("No API key available for AI-based matching")
            return []
        
        if not available_meshes:
            print("No available meshes provided")
            return []
        
        # Create the prompt
        prompt = self._create_ai_prompt(body_part, available_meshes, side)
        
        # Use the appropriate API based on the api_type
        if self.api_type == "gemini":
            return self._gemini_based_matching(prompt, available_meshes)
        else:
            return self._mistral_based_matching(prompt, available_meshes)
    
    def _mistral_based_matching(self, prompt: str, available_meshes: List[str]) -> List[str]:
        """Use Mistral AI to find matching meshes."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": "mistral-large-latest",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,  # Low temperature for more deterministic results
            "max_tokens": 1000
        }
        
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers=headers,
            json=data
        )
        
        if response.status_code != 200:
            print(f"API request failed with status code {response.status_code}: {response.text}")
            return []
        
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        
        # Extract the JSON array from the response
        try:
            # Find JSON array in the response
            import re
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                matches = json.loads(json_str)
                
                # Validate that all returned meshes are in the original list
                valid_matches = [mesh for mesh in matches if mesh in available_meshes]
                
                if valid_matches:
                    print(f"Mistral AI found {len(valid_matches)} matching meshes")
                    return valid_matches
                else:
                    print("Mistral AI returned matches, but none were in the available meshes list")
            else:
                print("Could not find JSON array in Mistral AI response")
        except json.JSONDecodeError:
            print(f"Failed to parse JSON from Mistral AI response: {content}")
        except Exception as e:
            print(f"Error processing Mistral AI response: {str(e)}")
        
        return []
    
    def _gemini_based_matching(self, prompt: str, available_meshes: List[str]) -> List[str]:
        """Use Google Gemini to find matching meshes via direct REST API call."""
        try:
            import requests
            
            # Prepare the API request
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
            
            # Prepare the request payload
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }]
            }
            
            # Set headers
            headers = {
                "Content-Type": "application/json"
            }
            
            # Make the API request
            print(f"Making direct REST API call to Gemini API with key: {self.api_key[:4]}...")
            response = requests.post(url, json=payload, headers=headers)
            
            # Check if the request was successful
            if response.status_code == 200:
                # Parse the response
                response_json = response.json()
                
                # Extract the content
                if 'candidates' in response_json and len(response_json['candidates']) > 0:
                    candidate = response_json['candidates'][0]
                    if 'content' in candidate and 'parts' in candidate['content']:
                        parts = candidate['content']['parts']
                        if len(parts) > 0 and 'text' in parts[0]:
                            content = parts[0]['text']
                            
                            # Extract the JSON array from the response
                            try:
                                # Find JSON array in the response
                                import re
                                json_match = re.search(r'\[.*\]', content, re.DOTALL)
                                if json_match:
                                    json_str = json_match.group(0)
                                    matches = json.loads(json_str)
                                    
                                    # Validate that all returned meshes are in the original list
                                    valid_matches = [mesh for mesh in matches if mesh in available_meshes]
                                    
                                    if valid_matches:
                                        print(f"Gemini API found {len(valid_matches)} matching meshes")
                                        return valid_matches
                                    else:
                                        print("Gemini API returned matches, but none were in the available meshes list")
                                else:
                                    print("Could not find JSON array in Gemini API response")
                            except json.JSONDecodeError:
                                print(f"Failed to parse JSON from Gemini API response: {content}")
                            except Exception as e:
                                print(f"Error processing Gemini API response: {str(e)}")
                        else:
                            print("No text found in Gemini API response parts")
                    else:
                        print("No content or parts found in Gemini API response candidate")
                else:
                    print("No candidates found in Gemini API response")
            else:
                print(f"Gemini API request failed with status code {response.status_code}: {response.text}")
        
        except Exception as e:
            print(f"Error using Gemini API: {str(e)}")
        
        return []
    
    def _local_fallback_matching(self, body_part: str, available_meshes: List[str], 
                               side: Optional[str] = None) -> List[str]:
        """
        Use local knowledge base to find matching meshes when AI is not available.
        
        Args:
            body_part: The body part to find meshes for
            available_meshes: List of available mesh names
            side: Optional side specification (left or right)
            
        Returns:
            List of matching mesh names
        """
        print(f"Using local fallback matching for '{body_part}'")
        
        # Clean up the body part name
        body_part = body_part.lower().strip()
        # Remove "side" if attached to body part
        if body_part.endswith(" side"):
            body_part = body_part[:-5]
        
        # Normalize body part name
        normalized_body_part = body_part.lower()
        
        # SPECIAL CASE FOR FOOT: If the body part is 'foot', be extremely aggressive
        if normalized_body_part == 'foot' or 'foot' in normalized_body_part:
            print(f"Special handling for foot-related body part: '{body_part}'")
            foot_related_terms = [
                'foot', 'toe', 'digit', 'metatarsal', 'tarsal', 'plantar', 'calcaneus',
                'hallux', 'phalanx', 'phalanges', 'interossei', 'lumbrical', 'flexor',
                'extensor', 'abductor', 'adductor', 'opponens', 'digiti', 'digitorum',
                'ankle', 'talus', 'fibular', 'retinaculum'
            ]
            
            foot_matches = []
            for mesh in available_meshes:
                mesh_lower = mesh.lower()
                # Check if any foot-related term is in the mesh name
                if any(term in mesh_lower for term in foot_related_terms):
                    # Check side constraints if applicable
                    if side and side.lower() in ['left', 'right']:
                        side_letter = 'l' if side.lower() == 'left' else 'r'
                        if mesh_lower.endswith(side_letter) or f".{side_letter}" in mesh_lower:
                            foot_matches.append(mesh)
                    else:
                        foot_matches.append(mesh)
            
            if foot_matches:
                print(f"Found {len(foot_matches)} foot-related matches using special handling")
                return foot_matches
        
        # Check for direct matches first
        direct_matches = []
        for mesh in available_meshes:
            mesh_lower = mesh.lower()
            if normalized_body_part in mesh_lower:
                # Check side constraints if applicable
                if side and side.lower() in ['left', 'right']:
                    side_letter = 'l' if side.lower() == 'left' else 'r'
                    if mesh_lower.endswith(side_letter) or f".{side_letter}" in mesh_lower:
                        direct_matches.append(mesh)
                else:
                    direct_matches.append(mesh)
        
        if direct_matches:
            print(f"Found {len(direct_matches)} direct matches for '{body_part}'")
            return direct_matches
        
        # Check synonyms
        synonyms = self.anatomical_knowledge.get('synonyms', {}).get(normalized_body_part, [])
        
        # Check if any known body part contains our search term
        for known_part, known_synonyms in self.anatomical_knowledge.get('synonyms', {}).items():
            if normalized_body_part in known_part or any(normalized_body_part in syn.lower() for syn in known_synonyms):
                synonyms.extend([known_part] + known_synonyms)
        
        # Remove duplicates
        synonyms = list(set(synonyms))
        
        if synonyms:
            print(f"Found synonyms for '{body_part}': {synonyms}")
            
            # Check for matches using synonyms
            synonym_matches = []
            for mesh in available_meshes:
                mesh_lower = mesh.lower()
                for synonym in synonyms:
                    if synonym.lower() in mesh_lower:
                        # Check side constraints if applicable
                        if side and side.lower() in ['left', 'right']:
                            side_letter = 'l' if side.lower() == 'left' else 'r'
                            if mesh_lower.endswith(side_letter) or f".{side_letter}" in mesh_lower:
                                synonym_matches.append(mesh)
                                break
                        else:
                            synonym_matches.append(mesh)
                            break
            
            if synonym_matches:
                print(f"Found {len(synonym_matches)} matches using synonyms for '{body_part}'")
                return synonym_matches
        
        # Check relationships
        related_terms = self.anatomical_knowledge.get('relationships', {}).get(normalized_body_part, [])
        
        # Check if any known relationship contains our search term
        for known_part, related in self.anatomical_knowledge.get('relationships', {}).items():
            if normalized_body_part in known_part:
                related_terms.extend(related)
        
        # Remove duplicates
        related_terms = list(set(related_terms))
        
        if related_terms:
            print(f"Found related terms for '{body_part}': {related_terms}")
            
            # Check for matches using related terms
            related_matches = []
            for mesh in available_meshes:
                mesh_lower = mesh.lower()
                for term in related_terms:
                    if term.lower() in mesh_lower:
                        # Check side constraints if applicable
                        if side and side.lower() in ['left', 'right']:
                            side_letter = 'l' if side.lower() == 'left' else 'r'
                            if mesh_lower.endswith(side_letter) or f".{side_letter}" in mesh_lower:
                                related_matches.append(mesh)
                                break
                        else:
                            related_matches.append(mesh)
                            break
            
            if related_matches:
                print(f"Found {len(related_matches)} matches using related terms for '{body_part}'")
                return related_matches
        
        # If no matches found, try a more aggressive approach
        print(f"No matches found using knowledge base, trying aggressive matching for '{body_part}'")
        return self._aggressive_matching(body_part, available_meshes, side)
    
    def _aggressive_matching(self, body_part: str, available_meshes: List[str],
                           side: Optional[str] = None) -> List[str]:
        """
        Aggressively find any mesh that might be related to the body part.
        
        Args:
            body_part: The body part to find meshes for
            available_meshes: List of available mesh names
            side: Optional side specification (left or right)
            
        Returns:
            List of matching mesh names
        """
        print(f"Using aggressive matching for '{body_part}'")
        
        # Normalize body part name
        body_part = body_part.lower().strip()
        
        # Define common body regions and related terms
        body_regions = {
            'foot': ['foot', 'toe', 'digit', 'metatarsal', 'tarsal', 'plantar', 'calcaneus',
                    'hallux', 'phalanx', 'phalanges', 'interossei', 'lumbrical'],
            'ankle': ['ankle', 'talus', 'calcaneus', 'fibular', 'retinaculum', 'malleolus'],
            'leg': ['leg', 'tibia', 'fibula', 'calf', 'shin', 'gastrocnemius', 'soleus'],
            'knee': ['knee', 'patella', 'patellar', 'meniscus', 'cruciate'],
            'thigh': ['thigh', 'femur', 'femoral', 'quadriceps', 'hamstring'],
            'hip': ['hip', 'pelvis', 'pelvic', 'ilium', 'iliac', 'ischium', 'pubis'],
            'back': ['back', 'spine', 'spinal', 'vertebra', 'vertebral', 'lumbar', 'thoracic'],
            'shoulder': ['shoulder', 'scapula', 'clavicle', 'acromial', 'deltoid'],
            'arm': ['arm', 'humerus', 'humeral', 'biceps', 'triceps'],
            'elbow': ['elbow', 'olecranon', 'ulnar', 'radial'],
            'forearm': ['forearm', 'ulna', 'radius', 'pronator', 'supinator'],
            'wrist': ['wrist', 'carpal', 'carpus'],
            'hand': ['hand', 'metacarpal', 'palm', 'palmar', 'finger', 'thumb', 'pollicis'],
            'neck': ['neck', 'cervical', 'throat', 'larynx', 'pharynx'],
            'head': ['head', 'skull', 'cranium', 'cranial', 'face', 'facial']
        }
        
        # Identify the body region
        target_region = None
        for region, terms in body_regions.items():
            if body_part == region or any(term in body_part for term in terms):
                target_region = region
                break
        
        if not target_region:
            print(f"Could not identify body region for '{body_part}'")
            return []
        
        print(f"Identified body region '{target_region}' for '{body_part}', using terms: {body_regions[target_region]}")
        
        # Get related terms for the body region
        related_terms = body_regions[target_region]
        
        # Special handling for foot vs hand to avoid confusion
        exclude_terms = []
        if target_region == 'foot' or target_region == 'ankle':
            exclude_terms = ['hand', 'palmar', 'pollicis', 'carpal', 'carpus', 'metacarpal']
        elif target_region == 'hand' or target_region == 'wrist':
            exclude_terms = ['foot', 'plantar', 'hallucis', 'tarsal', 'tarsus', 'metatarsal']
        
        # Find matching meshes
        matches = []
        for mesh in available_meshes:
            mesh_lower = mesh.lower()
            
            # Skip if mesh contains any exclude terms
            if any(exclude in mesh_lower for exclude in exclude_terms):
                continue
                
            # Check if any related term is in the mesh name
            if any(term in mesh_lower for term in related_terms):
                # Check side constraints if applicable
                if side and side.lower() in ['left', 'right']:
                    side_letter = 'l' if side.lower() == 'left' else 'r'
                    if mesh_lower.endswith(f".{side_letter}") or mesh_lower.endswith(side_letter):
                        matches.append(mesh)
                else:
                    matches.append(mesh)
        
        # Limit the number of matches to a reasonable count
        if len(matches) > 100:
            print(f"Found {len(matches)} potential matches, limiting to 100")
            matches = matches[:100]
        else:
            print(f"Aggressive matching found {len(matches)} potential matches for '{body_part}'")
        
        return matches
    
    def _get_default_meshes(self, body_part: str, available_meshes: List[str],
                          side: Optional[str] = None) -> List[str]:
        """
        Return default meshes for common body parts as a last resort.
        
        Args:
            body_part: The body part to find meshes for
            available_meshes: List of available mesh names
            side: Optional side specification (left or right)
            
        Returns:
            List of matching mesh names
        """
        print(f"Using default meshes for '{body_part}'")
        
        # Map common body parts to specific mesh name patterns
        default_mappings = {
            'foot': ['*foot*', '*plantar*', '*metatarsal*', '*tarsal*', '*digit*', '*toe*', 
                    '*phalanges*', '*interossei*', '*lumbrical*', '*flexor*', '*extensor*', 
                    '*abductor*', '*adductor*', '*opponens*', '*digiti*', '*digitorum*'],
            'ankle': ['*ankle*', '*talus*', '*calcaneus*', '*fibular*', '*retinaculum*'],
            'leg': ['*leg*', '*tibia*', '*fibula*', '*calf*', '*shin*', '*gastrocnemius*', '*soleus*'],
            'knee': ['*knee*', '*patella*', '*meniscus*', '*cruciate*', '*ligament*'],
            'thigh': ['*thigh*', '*femur*', '*quadricep*', '*hamstring*', '*femoral*'],
            'hip': ['*hip*', '*pelvis*', '*iliac*', '*gluteal*', '*gluteus*'],
            'back': ['*back*', '*spine*', '*vertebra*', '*lumbar*', '*thoracic*', '*cervical*'],
            'shoulder': ['*shoulder*', '*deltoid*', '*rotator*', '*cuff*', '*scapula*', '*clavicle*'],
            'arm': ['*arm*', '*humerus*', '*bicep*', '*tricep*', '*brachial*', '*brachii*'],
            'elbow': ['*elbow*', '*olecranon*', '*ulnar*'],
            'forearm': ['*forearm*', '*radius*', '*ulna*', '*radial*'],
            'wrist': ['*wrist*', '*carpal*', '*carpus*'],
            'hand': ['*hand*', '*finger*', '*thumb*', '*metacarpal*', '*phalanx*', '*palmar*'],
            'neck': ['*neck*', '*cervical*', '*throat*', '*larynx*'],
            'head': ['*head*', '*skull*', '*cranium*', '*face*', '*facial*'],
            'chest': ['*chest*', '*thorax*', '*rib*', '*pectoral*', '*sternum*'],
            'abdomen': ['*abdomen*', '*abdominal*', '*stomach*', '*belly*', '*core*']
        }
        
        # Find the best mapping
        patterns = []
        body_part_lower = body_part.lower()
        
        # First try exact matches
        if body_part_lower in default_mappings:
            patterns = default_mappings[body_part_lower]
        else:
            # Try partial matches
            for key, values in default_mappings.items():
                if key in body_part_lower or body_part_lower in key:
                    patterns = values
                    break
        
        if not patterns:
            print(f"No default patterns found for '{body_part}'")
            return []
        
        print(f"Using default patterns for '{body_part}': {patterns}")
        
        # Find meshes matching any pattern
        matches = []
        for mesh in available_meshes:
            mesh_lower = mesh.lower()
            for pattern in patterns:
                # Convert glob pattern to simple contains check
                search_term = pattern.replace('*', '')
                if search_term and search_term in mesh_lower:
                    # Check side if specified
                    if side and side.lower() in ['left', 'right']:
                        side_letter = 'l' if side.lower() == 'left' else 'r'
                        if mesh_lower.endswith(side_letter) or f".{side_letter}" in mesh_lower:
                            matches.append(mesh)
                            break
                    else:
                        matches.append(mesh)
                        break
        
        # Limit to a reasonable number
        max_matches = 30
        if len(matches) > max_matches:
            print(f"Limiting from {len(matches)} to {max_matches} default matches")
            matches = matches[:max_matches]
        
        print(f"Found {len(matches)} default matches for '{body_part}'")
        return matches
    
    def learn_from_correction(self, body_part: str, correct_meshes: List[str], 
                             incorrect_meshes: Optional[List[str]] = None):
        """
        Learn from user corrections to improve future matching.
        
        Args:
            body_part: The body part that was incorrectly matched
            correct_meshes: The correct mesh names for this body part
            incorrect_meshes: Optional list of incorrectly matched meshes
        """
        body_part_lower = body_part.lower()
        
        # Update match history
        self.match_history[body_part_lower] = correct_meshes
        
        # Extract potential new synonyms and relationships
        for mesh in correct_meshes:
            mesh_lower = mesh.lower()
            
            # Extract potential new term from mesh name
            terms = mesh_lower.split('_')
            for term in terms:
                if term != body_part_lower and len(term) > 3:  # Avoid short terms
                    # Add as related term if not already present
                    if body_part_lower not in self.anatomical_knowledge["relationships"]:
                        self.anatomical_knowledge["relationships"][body_part_lower] = []
                    
                    if term not in self.anatomical_knowledge["relationships"][body_part_lower]:
                        self.anatomical_knowledge["relationships"][body_part_lower].append(term)
        
        # Save updated knowledge
        self._save_anatomical_knowledge()
        logger.info(f"Learned correction for {body_part}: {correct_meshes}")
    
    def expand_knowledge_base(self, new_data: Dict[str, Any]):
        """
        Expand the anatomical knowledge base with new data.
        
        Args:
            new_data: Dictionary with new synonyms and relationships
        """
        # Update synonyms
        for term, synonyms in new_data.get("synonyms", {}).items():
            if term not in self.anatomical_knowledge["synonyms"]:
                self.anatomical_knowledge["synonyms"][term] = []
            
            for synonym in synonyms:
                if synonym not in self.anatomical_knowledge["synonyms"][term]:
                    self.anatomical_knowledge["synonyms"][term].append(synonym)
        
        # Update relationships
        for term, related in new_data.get("relationships", {}).items():
            if term not in self.anatomical_knowledge["relationships"]:
                self.anatomical_knowledge["relationships"][term] = []
            
            for rel in related:
                if rel not in self.anatomical_knowledge["relationships"][term]:
                    self.anatomical_knowledge["relationships"][term].append(rel)
        
        # Save updated knowledge
        self._save_anatomical_knowledge()
        logger.info("Anatomical knowledge base expanded")

    def _create_ai_prompt(self, body_part: str, available_meshes: List[str], 
                         side: Optional[str] = None) -> str:
        """
        Create a prompt for the AI model.
        
        Args:
            body_part: The body part to find meshes for
            available_meshes: List of available mesh names
            side: Optional side specification (left or right)
            
        Returns:
            Prompt string for the AI model
        """
        # Format the available meshes as a string
        meshes_str = "\n".join(available_meshes)
        
        # Create an extremely specific prompt that limits results to only the primary mesh
        prompt = f"""You are an expert anatomist and 3D medical visualization specialist. Your task is to identify ONLY THE SINGLE PRIMARY MESH from a 3D anatomical model that corresponds to a specific body part.

BODY PART: {body_part}
SIDE: {side if side else 'Not specified'}

AVAILABLE MESHES IN THE 3D MODEL:
{meshes_str}

INSTRUCTIONS:
1. Analyze the body part name and identify ONLY the single most specific anatomical structure that directly represents this body part.
2. DO NOT include related or surrounding structures - ONLY the exact primary structure.
3. STRICTLY LIMIT your selection to 1 MESH ONLY.
4. Pay special attention to side indicators in mesh names (e.g., '.l', '.r', 'left', 'right').
5. If a side is specified, ONLY include a mesh that matches that side.
6. Return ONLY the exact mesh name from the available list.
7. PRIORITIZE meshes that have the exact body part name in them.
8. For muscles, select ONLY the main muscle (not tendons, fascia, or other related tissues).
9. For joints, select ONLY the joint itself (not surrounding structures).
10. For bones, select ONLY the specific bone (not related structures).
11. Be extremely precise and specific - quality is essential.
12. If multiple meshes seem equally relevant, choose the one with the most specific name.

Return your answer as a JSON array containing ONLY ONE exact mesh name from the available list. Do not include any explanations or additional text. LIMIT YOUR RESPONSE TO 1 MESH ONLY.
"""
        return prompt

# Example usage
if __name__ == "__main__":
    service = AnatomicalAIService()
    test_meshes = [
        "Biceps_brachii_long_headl", 
        "Biceps_brachii_short_headl",
        "Brachialis_muscler", 
        "Deltoid_anterior_partl"
    ]
    matches = service.find_matching_meshes("biceps", test_meshes, "left")
    print(f"Matches for 'biceps' (left): {matches}") 