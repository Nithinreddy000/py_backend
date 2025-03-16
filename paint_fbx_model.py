import bpy
import json
import os
import sys
from pathlib import Path
import mathutils
import math
import datetime
import time
import argparse
import traceback
from typing import List, Dict, Any, Optional, Tuple

# Import our new AI service
try:
    from anatomical_ai_service import AnatomicalAIService
except ImportError:
    # Define a fallback class if the module is not available
    class AnatomicalAIService:
        def __init__(self, *args, **kwargs):
            print("WARNING: AnatomicalAIService module not found, using fallback methods only")
            self.use_local_fallback = True
            
        def find_matching_meshes(self, body_part, available_meshes, side=None):
            # Simple fallback implementation
            body_part_lower = body_part.lower()
            matches = []
            for mesh in available_meshes:
                if body_part_lower in mesh.lower():
                    matches.append(mesh)
            return matches

class InjuryVisualizer:
    INJURY_COLORS = {
        'active': (1.0, 0.0, 0.0, 1.0),     # Red for active injuries
        'past': (1.0, 0.5, 0.0, 1.0),       # Orange for past injuries
        'recovered': (0.0, 1.0, 0.0, 1.0),  # Green for recovered injuries
    }
    
    SEVERITY_ALPHA = {
        'mild': 0.85,
        'moderate': 0.95,
        'severe': 1.0
    }
    
    # Configuration for mesh painting behavior
    PAINTING_CONFIG = {
        'outer_mesh_alpha_multiplier': 0.0,  # Make outer meshes completely transparent
        'inner_mesh_alpha_multiplier': 1.0,  # Keep inner meshes fully visible
        'emission_strength': 20.0,           # Increased emission for better visibility
        'roughness': 0.9,                    # High roughness for non-shiny appearance
        'depth_test': False,                 # Disable depth test for better visibility
        'use_shadows': False,                # Disable shadows for better performance
        'use_backface_culling': False,       # Show backfaces
        'blend_method': 'HASHED',            # Use alpha hashed blend mode for better transparency sorting
        'shadow_method': 'NONE',             # No shadows for transparent materials
        'show_transparent': True,            # Show transparent materials
        'use_screen_refraction': False,      # Disable screen space refraction
        'use_screen_reflection': False,      # Disable screen space reflection
        'max_inner_meshes': 3,               # Reduced from 5 to 3 inner meshes
        'max_outer_meshes': 5,               # Reduced from 30 to 5 outer meshes
        'proximity_multiplier': 1.5,         # Reduced from 3.0 to 1.5 for stricter proximity detection
        'outer_emission_strength': 5.0,      # Emission strength for outer meshes
        'inner_emission_mix': 0.95,          # Mix factor for inner mesh emission
        'outer_emission_mix': 0.7,           # Mix factor for outer mesh emission
        'strict_side_matching': True,        # Strict side matching for left/right
        'use_topmost_mesh': True,            # Use topmost mesh feature
        'max_topmost_distance': 3.0,         # Reduced from 5.0 to 3.0 for stricter topmost mesh detection
        'xray_opacity': 1,                   # Opacity for x-ray effect (0-1)
        'xray_color': (0.8, 0.9, 1.0, 1.0),  # Blueish color for x-ray effect
        'xray_emission_strength': 5,         # Emission strength for x-ray effect
        'apply_xray_before_injuries': True   # Whether to apply x-ray before injury colors
    }
    
    # Updated list of specific outer meshes that should always be made transparent
    OUTER_MESHES = [
        # Original meshes
        'Deltoid_fascia',
        'Brachial_fascia',
        'Antebrachial_fascia',
        'Palmar_aponeurosis',
        'Platysma',
        'Pectoral_fascia',
        'Investing_abdominal_fascia',
        'Fascia_lata',
        'Crural_fascia',
        'subcutaneous_prepatellar_bursa',
        'subcutaneous_infrapatellar_bursa',
        'subcutaneous_bursa_of_tuberosity_of_tibia',
        'superior_fibular_retinaculum',
        'Epicranial_aponeurosis',
        'Frontalis_muscle',
        'Temporoparietalis_muscle',
        'Zygomaticus_minor_muscle',
        'Risorius_muscle',
        'orbicularis_oris_muscle',
        'Platysma',
        'Masseteric_fascia',
        'Depressor_anguli_oris',
        'Buchinator',
        'Zygomaticus_major_muscle',
        'Superficial_investing_cervical_fascia',
        'OCcipitalis_muscle',
        'Procerus_muscle',
        'Dorsa_fascia_of_hand',
        'Ilitibial_tract',
        'Popliteal_fascia',
        'Crucal_fascia',
        'Subcutaneous_calcaneal_bursa',
        
        # Additional meshes with exact names as provided by user
        'Deltoid_fascial',
        'Deltoid_fasciar',
        'Brachial_fascial',
        'Brachial_fasciar',
        'Antebrachial_fascial',
        'Antebrachial_fasciar',
        'Palmar_aponeurosisl',
        'Palmar_aponeurosisr',
        'Platysmal',
        'Platysmar',
        'Pectoral_fascial',
        'Pectoral_fasciar',
        'Investing_abdominal_fascial',
        'Investing_abdominal_fasciar',
        'Fascia_latal',
        'Fascia_latar',
        'Crural_fascial',
        'Crural_fasciar',
        'subcutaneous_prepatellar_bursal',
        'subcutaneous_prepatellar_bursar',
        'subcutaneous_infrapatellar_bursal',
        'subcutaneous_infrapatellar_bursar',
        'subcutaneous_bursa_of_tuberosity_of_tibial',
        'subcutaneous_bursa_of_tuberosity_of_tibiar',
        'superior_fibular_retinaculuml',
        'superior_fibular_retinaculumr',
        'Epicranial_aponeurosisl',
        'Epicranial_aponeurosisr',
        'Frontalis_musclel',
        'Frontalis_muscler',
        'Temporoparietalis_musclel',
        'Temporoparietalis_muscler',
        'Zygomaticus_minor_musclel',
        'Zygomaticus_minor_muscler',
        'Risorius_musclel',
        'Risorius_muscler',
        'orbicularis_oris_musclel',
        'orbicularis_oris_muscler',
        'Masseteric_fascial',
        'Masseteric_fasciar',
        'Depressor_anguli_orisl',
        'Depressor_anguli_orisr',
        'Buchinatorl',
        'Buchinatorr',
        'Zygomaticus_major_musclel',
        'Zygomaticus_major_muscler',
        'Superficial_investing_cervical_fascial',
        'Superficial_investing_cervical_fasciar',
        'OCcipitalis_musclel',
        'OCcipitalis_muscler',
        'Procerus_musclel',
        'Procerus_muscler',
        'Dorsa_fascia_of_handl',
        'Dorsa_fascia_of_handr',
        'Ilitibial_tractl',
        'Ilitibial_tractr',
        'Popliteal_fascial',
        'Popliteal_fasciar',
        'Crucal_fascial',
        'Crucal_fasciar',
        'Subcutaneous_calcaneal_bursal',
        'Subcutaneous_calcaneal_bursar'
    ]
    
    # Specific body part mappings to ensure correct mesh selection
    BODY_PART_MESH_MAPPING = {
        'neck': [
            'Neck',
            'Cervical spine',
            'Cervical',
            'Trapezius muscle',
            'Platysma',
            'Sternocleidomastoid muscle',
            'Sternocleidomastoid',
            'Larynx'
        ],
        'upper arm': [
            'Biceps brachii muscle',
            'Biceps brachii',
            'Biceps',
            'Bicep',
            'Brachialis muscle',
            'Brachialis',
            'Triceps brachii muscle',
            'Triceps brachii',
            'Triceps',
            'Brachioradialis muscle',
            'Brachioradialis',
            'Upper arm',
            'Arm muscles',
            'Arm muscle',
            'Arm'
        ],
        'biceps': [
            'Biceps brachii muscle', 
            'Biceps brachii',
            'Biceps',
            'Bicep',
            'Brachialis muscle',
            'Brachialis',
            'Upper arm',
            'Arm muscles',
            'Arm muscle'
        ],
        'thigh': [
            'Quadriceps femoris muscle',
            'Quadriceps femoris',
            'Quadriceps',
            'Quads',
            'Quad',
            'Rectus femoris muscle',
            'Rectus femoris',
            'Vastus lateralis muscle',
            'Vastus lateralis',
            'Vastus medialis muscle',
            'Vastus medialis',
            'Vastus intermedius muscle',
            'Vastus intermedius',
            'Hamstring muscles',
            'Hamstrings',
            'Hamstring',
            'Thigh',
            'Upper leg',
            'Femoral',
            'Femur'
        ],
        'quadriceps': [
            'Quadriceps femoris muscle',
            'Quadriceps femoris',
            'Quadriceps',
            'Quads',
            'Quad',
            'Rectus femoris muscle',
            'Rectus femoris',
            'Vastus lateralis muscle',
            'Vastus lateralis',
            'Vastus medialis muscle',
            'Vastus medialis',
            'Vastus intermedius muscle',
            'Vastus intermedius',
            'Thigh',
            'Upper leg',
            'Femoral'
        ],
        'shoulder': [
            'Deltoid muscle',
            'Supraspinatus muscle',
            'Infraspinatus muscle',
            'Teres minor muscle',
            'Teres major muscle',
            'Subscapularis muscle'
        ],
        'calf': [
            'Gastrocnemius muscle',
            'Soleus muscle',
            'Lateral head of gastrocnemius',
            'Medial head of gastrocnemius'
        ]
    }
    
    def __init__(self, fbx_path):
        print(f"Initializing InjuryVisualizer with FBX path: {fbx_path}")
        self.fbx_path = fbx_path
        # Initialize dictionaries before setup_scene
        self.original_materials = {}
        self.original_visibility = {}
        self.processed_body_parts = set()  # Track processed body parts to avoid duplicates
        
        # Initialize the AI service for improved mesh detection
        try:
            self.ai_service = AnatomicalAIService(use_local_fallback=True)
            print("Initialized AnatomicalAIService for improved mesh detection")
        except Exception as e:
            print(f"WARNING: Could not initialize AnatomicalAIService: {e}")
            self.ai_service = None
        
        self.setup_scene()
    
    def setup_scene(self):
        """Initialize Blender scene"""
        try:
            print("Setting up Blender scene...")
            # Clear existing scene
            bpy.ops.wm.read_factory_settings(use_empty=True)
            
            # Import FBX
            if not os.path.exists(self.fbx_path):
                raise FileNotFoundError(f"FBX file not found: {self.fbx_path}")
            
            print(f"Importing FBX from: {self.fbx_path}")
            
            # Redirect stdout to suppress Draco encoding logs if needed
            if not self.PAINTING_CONFIG.get('show_debug_logs', True):
                import sys
                from io import StringIO
                original_stdout = sys.stdout
                sys.stdout = StringIO()  # Redirect to string buffer
            
            # Import the FBX file
            bpy.ops.import_scene.fbx(filepath=self.fbx_path)
            
            # Restore stdout if it was redirected
            if not self.PAINTING_CONFIG.get('show_debug_logs', True):
                sys.stdout = original_stdout
            
            # Verify import was successful
            if len(bpy.data.objects) == 0:
                raise Exception("No objects were imported from the FBX file")
            
            print(f"Successfully imported {len(bpy.data.objects)} objects")
            
            # Store original materials and visibility
            for obj in bpy.data.objects:
                if obj.type == 'MESH':
                    if obj.material_slots:
                        self.original_materials[obj.name] = obj.material_slots[0].material.copy()
                    else:
                        self.original_materials[obj.name] = None
                    self.original_visibility[obj.name] = obj.hide_viewport
            
            # Setup camera
            bpy.ops.object.camera_add()
            self.camera = bpy.context.active_object
            
            # Setup lighting
            bpy.ops.object.light_add(type='SUN')
            self.light = bpy.context.active_object
            
            # Setup viewport for better visualization
            for area in bpy.context.screen.areas:
                if area.type == 'VIEW_3D':
                    for space in area.spaces:
                        if space.type == 'VIEW_3D':
                            space.shading.type = 'SOLID'
                            space.shading.use_scene_lights = True
                            space.shading.use_scene_world = False  # Disable world for better performance
                            space.shading.light = 'FLAT'  # Use flat lighting for better performance
                            space.shading.show_specular_highlight = False  # Disable specular for better performance
            
            # Set up rendering with Workbench renderer instead of EEVEE
            bpy.context.scene.render.engine = 'BLENDER_WORKBENCH'
            
            # Configure Workbench settings for better visualization with minimal settings
            if hasattr(bpy.context.scene, 'display'):
                bpy.context.scene.display.shading.light = 'FLAT'  # Flat lighting is faster
                bpy.context.scene.display.shading.color_type = 'MATERIAL'
                bpy.context.scene.display.shading.show_object_outline = False  # Disable outline for better performance
                bpy.context.scene.display.shading.show_specular_highlight = False  # Disable specular for better performance
            
            print("Scene setup completed successfully")
            
        except Exception as e:
            print(f"Error setting up scene: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    def _get_related_anatomical_terms(self, body_part):
        """Get related anatomical terms for a body part using a more comprehensive approach"""
        body_part = body_part.lower()
        
        # Define anatomical mappings for common body parts
        anatomical_mappings = {
            'biceps': ['bicep', 'biceps', 'brachii', 'arm', 'upper arm'],
            'triceps': ['tricep', 'triceps', 'brachii', 'arm', 'upper arm'],
            'deltoid': ['deltoid', 'shoulder', 'delt'],
            'gastrocnemius': ['gastrocnemius', 'calf', 'leg', 'gastroc', 'soleus'],
            'quadriceps': ['quad', 'quadricep', 'quadriceps', 'thigh', 'femur', 'leg', 'anterior', 'femoral', 'vastus'],
            'hamstring': ['hamstring', 'thigh', 'leg', 'posterior', 'femur', 'biceps femoris'],
            'pectoralis': ['pec', 'chest', 'pectoral', 'pectoralis'],
            'latissimus': ['lat', 'back', 'latissimus', 'dorsi'],
            'trapezius': ['trap', 'back', 'trapezius', 'shoulder'],
            'gluteus': ['glute', 'buttock', 'gluteus', 'maximus'],
            'abdominals': ['abs', 'abdomen', 'rectus', 'abdominis'],
            'shoulder': ['shoulder', 'deltoid', 'rotator', 'cuff', 'supraspinatus', 'infraspinatus', 'teres'],
            'knee': ['knee', 'patella', 'leg', 'joint'],
            'ankle': ['ankle', 'foot', 'tarsal', 'joint'],
            'wrist': ['wrist', 'hand', 'carpal', 'joint'],
            'elbow': ['elbow', 'arm', 'joint', 'ulnar'],
            'hip': ['hip', 'pelvis', 'joint', 'iliac'],
            'neck': ['neck', 'cervical', 'spine'],
            'back': ['back', 'spine', 'vertebra', 'lumbar', 'thoracic'],
            'chest': ['chest', 'thorax', 'rib', 'pectoral', 'sternum'],
            'arm': ['arm', 'humerus', 'bicep', 'tricep', 'brachial', 'brachii'],
            'forearm': ['forearm', 'radius', 'ulna', 'wrist'],
            'thigh': ['thigh', 'femur', 'quadricep', 'quadriceps', 'quad', 'hamstring', 'femoral'],
            'leg': ['leg', 'tibia', 'fibula', 'calf', 'shin', 'gastrocnemius'],
            'foot': ['foot', 'toe', 'metatarsal', 'calcaneus', 'heel', 'plantar', 'tarsal', 'phalanges', 'digit', 'hallux', 'talus', 'navicular', 'cuboid', 'cuneiform', 'interossei'],
            'upper arm': ['bicep', 'tricep', 'brachii', 'humerus', 'arm', 'upper arm', 'brachialis'],
            'calf': ['calf', 'gastrocnemius', 'soleus', 'leg', 'lower leg', 'achilles']
        }
        
        # Find related terms from anatomical mappings
        related_terms = []
        
        # First check for exact matches
        if body_part in anatomical_mappings:
            related_terms.extend(anatomical_mappings[body_part])
            print(f"  (INFO: Found related anatomical terms for '{body_part}': {', '.join(anatomical_mappings[body_part])})")
        
        # Then check for partial matches
        for key, terms in anatomical_mappings.items():
            if key not in body_part and (key in body_part or any(term in body_part for term in terms)):
                related_terms.extend(terms)
                print(f"  (INFO: Found related anatomical terms for '{body_part}' via '{key}': {', '.join(terms)})")
        
        # Add the original body part to the related terms
        if body_part not in related_terms:
            related_terms.append(body_part)
        
        # Remove duplicates while preserving order
        unique_terms = []
        for term in related_terms:
            if term not in unique_terms:
                unique_terms.append(term)
        
        return unique_terms
    
    def create_injury_material(self, injury_type, severity, alpha_multiplier=1.0, is_inner=False, is_outer=False):
        """Create material for injury visualization"""
        # Use descriptive material name
        material_name_suffix = 'inner' if is_inner else ('outer' if is_outer else 'default')
        material_name = f"Injury_{injury_type}_{severity}_{material_name_suffix}_{time.time()}"
        
        # Get injury color based on type
        injury_color = self.INJURY_COLORS.get(injury_type, (1.0, 0.0, 0.0, 1.0))  # Default to red if not found
        
        # Create new material
        material = bpy.data.materials.new(name=material_name)
        material.use_nodes = False  # Use simpler material model for better performance
        
        # Set alpha transparency based on severity and mesh type
        severity_alpha = self.SEVERITY_ALPHA.get(severity, 1.0)
        
        # Set different alpha for inner vs outer meshes
        if is_inner:
            # Inner meshes should be fully visible with injury color
            alpha = severity_alpha * self.PAINTING_CONFIG.get('inner_mesh_alpha_multiplier', 1.0) * alpha_multiplier
            print(f"Creating inner mesh material with alpha {alpha}")
        elif is_outer:
            # Outer meshes should be transparent
            alpha = 0.0  # Force complete transparency for outer meshes
            print(f"Creating outer mesh material with alpha {alpha} (transparent)")
        else:
            # Default case
            alpha = severity_alpha * alpha_multiplier
        
        # Set material properties with the right alpha
        material.diffuse_color = (injury_color[0], injury_color[1], injury_color[2], alpha)
        
        # Set emission for better visibility
        emission_strength = self.PAINTING_CONFIG.get('emission_strength', 1.0)
        if is_inner:
            emission_mix = self.PAINTING_CONFIG.get('inner_emission_mix', 0.5)
            emission_strength = self.PAINTING_CONFIG.get('emission_strength', 1.0)
        elif is_outer:
            emission_mix = self.PAINTING_CONFIG.get('outer_emission_mix', 0.2)
            emission_strength = self.PAINTING_CONFIG.get('outer_emission_strength', 1.0)
        else:
            emission_mix = 0.5
        
        material.roughness = self.PAINTING_CONFIG.get('roughness', 0.9)
        
        # Set transparency options
        material.blend_method = 'HASHED'  # Change from BLEND to HASHED for better transparency sorting
        material.shadow_method = 'NONE'
        material.use_backface_culling = self.PAINTING_CONFIG.get('use_backface_culling', False)
        
        return material
    
    def find_topmost_mesh(self, target_mesh_name):
        """Find the topmost visible mesh above the target mesh"""
        target_obj = bpy.data.objects.get(target_mesh_name)
        if not target_obj:
            print(f"  (ERROR: Target mesh '{target_mesh_name}' not found in scene)")
            return None
            
        # If topmost mesh feature is disabled, just return the target mesh
        if not self.PAINTING_CONFIG.get('use_topmost_mesh', False):
            return target_obj

        # Get target mesh's center and create a ray from above
        target_center = target_obj.matrix_world @ target_obj.location
        ray_origin = target_center.copy()
        ray_origin.z += 10.0  # Start ray from above
        ray_direction = mathutils.Vector((0, 0, -1))  # Ray pointing down

        # Find all intersecting meshes
        intersecting_meshes = []
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                # Skip meshes that are clearly in different body regions
                if self._is_different_body_region(target_mesh_name, obj.name):
                    continue
                    
                # Convert ray to object space
                try:
                    matrix_inv = obj.matrix_world.inverted()
                    ray_origin_obj = matrix_inv @ ray_origin
                    ray_direction_obj = matrix_inv.to_3x3() @ ray_direction

                    # Check for intersection
                    success, location, normal, face_index = obj.ray_cast(ray_origin_obj, ray_direction_obj)
                    if success:
                        # Store mesh and its world space intersection point
                        world_location = obj.matrix_world @ location
                        distance = (world_location - target_center).length
                        
                        # Only consider meshes that are close to the target
                        max_distance = self.PAINTING_CONFIG.get('max_topmost_distance', 3.0)
                        if distance < max_distance:  # Limit to reasonable distance
                            intersecting_meshes.append((obj, distance, world_location.z))
                except Exception as e:
                    print(f"  (WARNING: Error ray-casting on mesh '{obj.name}': {str(e)})")
                    continue

        if not intersecting_meshes:
            print(f"  (INFO: No intersecting meshes found, using target mesh '{target_mesh_name}' directly)")
            return target_obj  # Fall back to target mesh if no intersections

        # Sort by Z coordinate (highest first) and distance to target
        intersecting_meshes.sort(key=lambda x: (-x[2], x[1]))
        
        # Prefer the target mesh if it's in the list of intersecting meshes
        for i, (obj, _, _) in enumerate(intersecting_meshes):
            if obj.name == target_mesh_name:
                return obj
                
        # Return the topmost mesh (first in sorted list)
        topmost_obj = intersecting_meshes[0][0]
        print(f"  (INFO: Using topmost mesh '{topmost_obj.name}' instead of '{target_mesh_name}')")
        return topmost_obj
    
    def _is_different_body_region(self, mesh1, mesh2):
        """Check if two meshes are in different body regions"""
        # Extract region from mesh names
        region1 = self._extract_region(mesh1)
        region2 = self._extract_region(mesh2)
        
        # If we couldn't determine regions, assume they're not different
        if not region1 or not region2:
                return False
            
        # Check if regions are different
        return region1 != region2
    
    def paint_injury(self, mesh_name, injury, is_inner=False, is_outer=False):
        """Paint a mesh with injury visualization material"""
        if isinstance(mesh_name, str):
            # Ensure we have the actual object
            mesh_obj = None
            for obj in bpy.data.objects:
                if obj.name.lower() == mesh_name.lower():
                    mesh_obj = obj
                    break
            
            if not mesh_obj:
                print(f"  (WARNING: Could not find mesh with name '{mesh_name}')")
                return False
        else:
            # It's already an object
            mesh_obj = mesh_name
            mesh_name = mesh_obj.name
        
        # Store original material for later restoration
        self.original_materials[mesh_name] = [slot.material for slot in mesh_obj.material_slots]
        self.original_visibility[mesh_name] = mesh_obj.hide_viewport
        
        # Make sure the object is visible
        mesh_obj.hide_viewport = False
        mesh_obj.hide_render = False
        
        # Check if this is a specific outer mesh that should be forced transparent
        # Normalize mesh name by removing l/r suffix for matching
        normalized_mesh_name = mesh_name.lower()
        if normalized_mesh_name.endswith('l') or normalized_mesh_name.endswith('r'):
            normalized_mesh_name = normalized_mesh_name[:-1]
        
        # Special handling for foot vs hand confusion
        body_part = injury.get('bodyPart', '').lower()
        
        # If dealing with foot injuries, skip hand-related meshes
        if 'foot' in body_part or 'ankle' in body_part:
            if any(term in normalized_mesh_name for term in ['hand', 'palmar', 'pollicis', 'carpal', 'carpus', 'metacarpal']):
                print(f"  (INFO: Skipping hand-related mesh '{mesh_name}' for foot/ankle injury)")
                return False
                
        # If dealing with hand injuries, skip foot-related meshes
        if 'hand' in body_part or 'wrist' in body_part:
            if any(term in normalized_mesh_name for term in ['foot', 'plantar', 'hallucis', 'tarsal', 'tarsus', 'metatarsal']):
                print(f"  (INFO: Skipping foot-related mesh '{mesh_name}' for hand/wrist injury)")
                return False
        
        # Check against outer meshes list
        is_specific_outer = False
        for outer_mesh in self.OUTER_MESHES:
            outer_lower = outer_mesh.lower()
            if outer_lower in normalized_mesh_name or normalized_mesh_name in outer_lower:
                is_specific_outer = True
                print(f"  (INFO: Detected outer mesh '{mesh_name}' matching entry '{outer_mesh}')")
                break
        
        # Special handling for known muscle groups
        is_biceps = 'bicep' in normalized_mesh_name.lower() or 'brachii' in normalized_mesh_name.lower()
        is_quadriceps = 'quad' in normalized_mesh_name.lower() or 'femoris' in normalized_mesh_name.lower()
        is_deltoid = 'deltoid' in normalized_mesh_name.lower() or 'shoulder' in normalized_mesh_name.lower()
        
        # Determine if mesh is on inner or outer list
        if is_inner and is_specific_outer:
            print(f"  (WARNING: Mesh '{mesh_name}' is marked as both inner and outer mesh, treating as inner)")
        elif is_specific_outer:
            is_outer = True
            print(f"  (INFO: Treating '{mesh_name}' as outer mesh due to name matching outer mesh list)")
        elif is_biceps and not is_inner:
            print(f"  (INFO: Detected biceps muscle '{mesh_name}')")
            is_inner = True  # Force biceps to be treated as inner mesh
        elif is_quadriceps and not is_inner:
            print(f"  (INFO: Detected quadriceps muscle '{mesh_name}')")
            is_inner = True  # Force quadriceps to be treated as inner mesh
        elif is_deltoid and not is_inner:
            print(f"  (INFO: Detected deltoid/shoulder muscle '{mesh_name}')")
            is_inner = True  # Force deltoid to be treated as inner mesh
        
        # Determine alpha multiplier based on mesh type
        alpha_multiplier = 1.0
        if is_outer:
            alpha_multiplier = self.PAINTING_CONFIG.get('outer_mesh_alpha_multiplier', 0.0)
            print(f"  (INFO: Using outer mesh alpha multiplier: {alpha_multiplier} for '{mesh_name}')")
        elif is_inner:
            alpha_multiplier = self.PAINTING_CONFIG.get('inner_mesh_alpha_multiplier', 1.0)
            print(f"  (INFO: Using inner mesh alpha multiplier: {alpha_multiplier} for '{mesh_name}')")
        
        # Create injury material
        material = self.create_injury_material(
            injury['status'], 
            injury['severity'],
            alpha_multiplier=alpha_multiplier,
            is_inner=is_inner,
            is_outer=is_outer
        )
        
        # Apply material to all slots of the mesh
        if mesh_obj.data.materials:
            # Replace all material slots
            for i in range(len(mesh_obj.data.materials)):
                mesh_obj.data.materials[i] = material
        else:
            # No existing materials, add a new one
            mesh_obj.data.materials.append(material)
        
        return True

    def _extract_region(self, mesh_name):
        """Extract body region from mesh name"""
        # Common body regions to check for
        regions = {
            'head': ['head', 'skull', 'cranium', 'face', 'jaw', 'mandible'],
            'neck': ['neck', 'cervical'],
            'shoulder': ['shoulder', 'clavicle', 'scapula'],
            'arm': ['arm', 'humerus', 'bicep', 'tricep', 'brachii'],
            'elbow': ['elbow'],
            'forearm': ['forearm', 'radius', 'ulna'],
            'wrist': ['wrist', 'carpal'],
            'hand': ['hand', 'finger', 'thumb', 'palm', 'metacarpal', 'phalanx'],
            'chest': ['chest', 'thorax', 'thoracic', 'pectoral', 'sternum', 'rib'],
            'abdomen': ['abdomen', 'abdominal', 'stomach', 'belly'],
            'back': ['back', 'spine', 'spinal', 'vertebra', 'vertebrae', 'lumbar'],
            'hip': ['hip', 'pelvis', 'pelvic', 'ilium', 'iliac'],
            'thigh': ['thigh', 'femur', 'quadricep', 'quadriceps', 'quad', 'hamstring', 'femoral'],
            'knee': ['knee', 'patella', 'patellar'],
            'leg': ['leg', 'shin', 'calf', 'tibia', 'fibula', 'gastrocnemius'],
            'ankle': ['ankle', 'tarsal'],
            'foot': ['foot', 'feet', 'toe', 'metatarsal', 'calcaneus', 'heel']
        }
        
        # Convert mesh name to lowercase for case-insensitive matching
        mesh_lower = mesh_name.lower()
        
        # Check for each region
        for region, keywords in regions.items():
            for keyword in keywords:
                if keyword in mesh_lower:
                    return region
        
        # If no region found, return None
        return None
    
    def is_mesh_on_side(self, mesh_name, side):
        """Check if a mesh is on the specified side (left or right)"""
        if not side or side.lower() not in ['left', 'right']:
            return True  # If no side specified, consider it a match
            
        mesh_lower = mesh_name.lower()
        side_lower = side.lower()
        
        # Check for explicit side indicators in the mesh name
        left_indicators = ['left', 'l_', '_l', '.l', 'l.', 'l ', ' l', 'lft', 'lt']
        right_indicators = ['right', 'r_', '_r', '.r', 'r.', 'r ', ' r', 'rgt', 'rt']
        
        # Special check for 'l' or 'r' at the end of the mesh name
        if mesh_lower.endswith('l'):
            print(f"  (INFO: Mesh '{mesh_name}' identified as LEFT side due to 'l' suffix")
            return side_lower == 'left'
            
        if mesh_lower.endswith('r'):
            print(f"  (INFO: Mesh '{mesh_name}' identified as RIGHT side due to 'r' suffix")
            return side_lower == 'right'
        
        # Check for opposite side indicators
        opposite_indicators = left_indicators if side_lower == 'right' else right_indicators
        for indicator in opposite_indicators:
            if indicator in mesh_lower:
                print(f"  (INFO: Mesh '{mesh_name}' rejected due to opposite side indicator '{indicator}'")
                return False  # Mesh has indicator for the opposite side
        
        # Check for matching side indicators
        matching_indicators = right_indicators if side_lower == 'right' else left_indicators
        for indicator in matching_indicators:
            if indicator in mesh_lower:
                print(f"  (INFO: Mesh '{mesh_name}' matched due to side indicator '{indicator}'")
                return True  # Mesh has indicator for the matching side
                
        # If no explicit indicators, check mesh position
        obj = bpy.data.objects.get(mesh_name)
        if obj:
            # Get object's world position
            position = obj.matrix_world.translation
            
            # Check if object is on the left or right side based on X coordinate
            # In Blender, negative X is typically left, positive X is right
            if side_lower == 'left' and position.x < 0:
                print(f"  (INFO: Mesh '{mesh_name}' identified as LEFT side due to position (X={position.x})")
                return True
            elif side_lower == 'right' and position.x > 0:
                print(f"  (INFO: Mesh '{mesh_name}' identified as RIGHT side due to position (X={position.x})")
                return True
            else:
                print(f"  (INFO: Mesh '{mesh_name}' position (X={position.x}) does not match requested side '{side_lower}')")
                
        # If we couldn't determine the side, return True to avoid filtering out potentially relevant meshes
        print(f"  (INFO: Could not determine side for mesh '{mesh_name}', including it anyway)")
        return True
    
    def find_inner_meshes(self, muscle_name, injury):
        """Find inner meshes related to the injured muscle using a dynamic approach"""
        body_part = injury.get('bodyPart', '').lower() if injury.get('bodyPart') else muscle_name.lower()
        side = injury.get('side', '').lower()
        
        print(f"Finding inner meshes for {body_part} ({side} side)...")
        
        # Define exclusion terms based on body part
        exclusion_terms = []
        if 'foot' in body_part or 'ankle' in body_part:
            exclusion_terms = ['hand', 'palmar', 'pollicis', 'carpal', 'carpus', 'metacarpal']
            print(f"  (INFO: Will exclude hand-related meshes for foot/ankle injury)")
        elif 'hand' in body_part or 'wrist' in body_part:
            exclusion_terms = ['foot', 'plantar', 'hallucis', 'tarsal', 'tarsus', 'metatarsal']
            print(f"  (INFO: Will exclude foot-related meshes for hand/wrist injury)")
        
        # Get related anatomical terms for the body part
        related_terms = self._get_related_anatomical_terms(body_part)
        
        # Find meshes that match any of the related terms
        inner_meshes = []
        for obj in bpy.data.objects:
            if obj.type != 'MESH':
                continue
                
            # Skip meshes that match exclusion terms
            obj_name_lower = obj.name.lower()
            if exclusion_terms and any(term in obj_name_lower for term in exclusion_terms):
                print(f"  (INFO: Excluding mesh '{obj.name}' due to exclusion terms)")
                continue
                
            # Check if mesh name contains any related term
            for term in related_terms:
                if term.lower() in obj_name_lower:
                    # Check if mesh is on the correct side
                    if self.is_mesh_on_side(obj.name, side):
                        # Additional filtering: Check if the mesh name directly contains the body part name
                        # This makes the matching more strict
                        body_part_words = body_part.split()
                        if any(word in obj_name_lower for word in body_part_words if len(word) > 3):
                            print(f"  (INFO: Found mesh '{obj.name}' with direct match to body part '{body_part}')")
                            inner_meshes.append(obj)
                            break
                        else:
                            # If not a direct match, only include if it's a very specific related term
                            if len(term) > 5:  # Only use longer, more specific terms
                                print(f"  (INFO: Found mesh '{obj.name}' with related term '{term}')")
                                inner_meshes.append(obj)
                                break
        
        print(f"Found {len(inner_meshes)} inner meshes for {body_part}")
        
        # If no inner meshes found, try a more aggressive search
        if not inner_meshes:
            print(f"  (WARNING: No inner meshes found for '{body_part}'. Trying alternative search...)")
            
            # Try to find any mesh that might be related to the body part
            # Split the body part into words and search for each word
            body_part_words = body_part.split()
            for obj in bpy.data.objects:
                if obj.type != 'MESH':
                    continue
                
                obj_name_lower = obj.name.lower()
                
                # Skip meshes that match exclusion terms
                if exclusion_terms and any(term in obj_name_lower for term in exclusion_terms):
                    continue
                    
                # Check if mesh name contains any word from the body part
                for word in body_part_words:
                    if len(word) > 3 and word in obj_name_lower:  # Only use words with more than 3 characters
                        # Check side constraints if applicable
                        if self.PAINTING_CONFIG.get('strict_side_matching', True) and side:
                            if not self.is_mesh_on_side(obj.name, side):
                                continue
                        inner_meshes.append(obj)  # Store the object directly
                        print(f"  (INFO: Found mesh '{obj.name}' with partial match to '{word}')")
                        break
                
            # If still no meshes found, use a broader search based on body region
            if not inner_meshes:
                print(f"  (WARNING: Still no meshes found for '{body_part}'. Searching by body region...)")
                
                # Determine the general body region
                body_region = self._determine_body_region(body_part)
                print(f"  (INFO: Determined body region '{body_region}' for '{body_part}')")
                
                # Find meshes in the same body region
                for obj in bpy.data.objects:
                    if obj.type != 'MESH':
                        continue
                        
                    obj_region = self._extract_region(obj.name)
                    if obj_region == body_region:
                        # Check if mesh is on the correct side
                        if self.is_mesh_on_side(obj.name, side):
                            # Additional filtering: Only include meshes that have some similarity to the body part
                            obj_name_lower = obj.name.lower()
                            body_part_chars = set(body_part.replace(" ", ""))
                            obj_name_chars = set(obj_name_lower.replace(" ", ""))
                            similarity = len(body_part_chars.intersection(obj_name_chars)) / len(body_part_chars)
                            
                            if similarity > 0.3:  # At least 30% character overlap
                                print(f"  (INFO: Found mesh '{obj.name}' in body region '{body_region}' with similarity {similarity:.2f})")
                                inner_meshes.append(obj)
                
                # Limit to a reasonable number of meshes
                if len(inner_meshes) > self.PAINTING_CONFIG['max_inner_meshes']:
                    print(f"  (INFO: Limiting from {len(inner_meshes)} to {self.PAINTING_CONFIG['max_inner_meshes']} inner meshes)")
                    inner_meshes = inner_meshes[:self.PAINTING_CONFIG['max_inner_meshes']]
        
        # If still no meshes found, use visible meshes on the correct side as a last resort
        if not inner_meshes:
            print(f"  (WARNING: No specific meshes found for '{body_part}'. Using visible meshes as last resort.)")
            visible_meshes = [obj for obj in bpy.data.objects if obj.type == 'MESH' and not obj.hide_viewport and self.is_mesh_on_side(obj.name, side)]
            
            # Take a few visible meshes
            max_fallback = min(2, len(visible_meshes))  # Reduced from 3 to 2
            inner_meshes = visible_meshes[:max_fallback]
            print(f"  (INFO: Using {len(inner_meshes)} visible meshes as fallback)")
        
        return inner_meshes
    
    def _determine_body_region(self, body_part):
        """Determine the general body region for a body part"""
        body_part = body_part.lower()
        
        # Define body regions and their associated terms
        body_regions = {
            'head': ['head', 'skull', 'face', 'jaw', 'cranium', 'brain'],
            'neck': ['neck', 'cervical', 'throat'],
            'shoulder': ['shoulder', 'deltoid', 'rotator cuff', 'clavicle', 'scapula'],
            'arm': ['arm', 'bicep', 'tricep', 'humerus', 'brachii', 'upper arm'],
            'elbow': ['elbow', 'olecranon'],
            'forearm': ['forearm', 'radius', 'ulna', 'wrist'],
            'hand': ['hand', 'finger', 'thumb', 'palm', 'wrist'],
            'chest': ['chest', 'pectoral', 'thorax', 'rib', 'sternum'],
            'abdomen': ['abdomen', 'stomach', 'abs', 'core'],
            'back': ['back', 'spine', 'vertebra', 'lumbar', 'thoracic'],
            'hip': ['hip', 'pelvis', 'iliac', 'sacrum'],
            'thigh': ['thigh', 'quadricep', 'hamstring', 'femur', 'upper leg'],
            'knee': ['knee', 'patella', 'meniscus'],
            'leg': ['leg', 'calf', 'shin', 'tibia', 'fibula', 'gastrocnemius', 'lower leg'],
            'ankle': ['ankle', 'talus', 'calcaneus'],
            'foot': ['foot', 'toe', 'heel', 'metatarsal', 'plantar', 'tarsal', 'phalanges', 'digit', 'hallux', 'navicular', 'cuboid', 'cuneiform', 'interossei']
        }
        
        # Check each region for matches
        for region, terms in body_regions.items():
            if any(term in body_part for term in terms):
                return region
        
        # Default to 'unknown' if no match found
        return 'unknown'
    
    def find_outer_visible_meshes(self, muscle_name, injury):
        """Find outer visible meshes that should be painted to show the injury location"""
        print(f"Finding outer visible meshes for {muscle_name}...")
        
        # Get injury details
        status = injury.get('status', 'active')
        side = injury.get('side', None)
        body_part = injury.get('bodyPart', '').lower() if injury.get('bodyPart') else ''
        
        # Define exclusion terms based on body part
        exclusion_terms = []
        if 'foot' in body_part or 'ankle' in body_part:
            exclusion_terms = ['hand', 'palmar', 'pollicis', 'carpal', 'carpus', 'metacarpal']
            print(f"  (INFO: Will exclude hand-related meshes for foot/ankle injury)")
        elif 'hand' in body_part or 'wrist' in body_part:
            exclusion_terms = ['foot', 'plantar', 'hallucis', 'tarsal', 'tarsus', 'metatarsal']
            print(f"  (INFO: Will exclude foot-related meshes for hand/wrist injury)")
        
        # Determine max outer meshes based on injury status - use much smaller values
        if status == 'active':
            max_outer = self.PAINTING_CONFIG.get('max_outer_meshes', 5)
        elif status == 'past':
            max_outer = self.PAINTING_CONFIG.get('max_outer_meshes', 3)
        else:  # recovered
            max_outer = self.PAINTING_CONFIG.get('max_outer_meshes', 2)
        
        # Get the target mesh
        target_obj = None
        if isinstance(muscle_name, str):
            target_obj = bpy.data.objects.get(muscle_name)
        elif hasattr(muscle_name, 'name'):
            target_obj = muscle_name  # It's already an object
            muscle_name = target_obj.name
        
        if not target_obj:
            print(f"  (ERROR: Target muscle '{muscle_name}' not found in scene)")
            return []

        # Find the topmost mesh if enabled
        topmost_obj = self.find_topmost_mesh(muscle_name)
        if topmost_obj and topmost_obj.name != muscle_name:
            print(f"  (INFO: Using topmost mesh '{topmost_obj.name}' as reference)")
            target_obj = topmost_obj
            
        # Get target mesh's center
        target_center = target_obj.matrix_world @ target_obj.location
        
        # Determine the body region for filtering
        body_region = self._extract_region(muscle_name)
        if not body_region and body_part:
            body_region = self._determine_body_region(body_part)
        
        print(f"  (INFO: Using body region '{body_region}' for filtering outer meshes)")
        
        # First, check for specific outer meshes from our predefined list
        specific_outer_meshes = []
        for obj in bpy.data.objects:
            if obj.type != 'MESH' or obj.hide_viewport:
                continue
                
            if obj.name == target_obj.name:
                continue
                    
            # Check side constraints if applicable
            if side and not self.is_mesh_on_side(obj.name, side):
                continue
            
            # Skip meshes that match exclusion terms
            obj_name_lower = obj.name.lower()
            if exclusion_terms and any(term in obj_name_lower for term in exclusion_terms):
                print(f"  (INFO: Excluding mesh '{obj.name}' due to exclusion terms)")
                continue
            
            # Check if this mesh is in our predefined list of outer meshes
            obj_base_name = obj.name.rstrip('lr')  # Remove potential 'l' or 'r' suffix
            for outer_mesh in self.OUTER_MESHES:
                if outer_mesh.lower() in obj.name.lower() or outer_mesh.lower() in obj_base_name.lower():
                    # Calculate distance for sorting
                    obj_center = obj.matrix_world @ obj.location
                    distance = (obj_center - target_center).length
                    
                    # Only include if it's close enough to the target
                    obj_size = max(obj.dimensions.x, obj.dimensions.y, obj.dimensions.z)
                    target_size = max(target_obj.dimensions.x, target_obj.dimensions.y, target_obj.dimensions.z)
                    threshold = (obj_size + target_size) * self.PAINTING_CONFIG.get('proximity_multiplier', 1.5)
                    
                    if distance < threshold:
                        specific_outer_meshes.append((obj.name, distance))
                        print(f"  (INFO: Found specific outer mesh '{obj.name}' matching '{outer_mesh}' at distance {distance:.2f})")
                    break
        
        # Sort specific outer meshes by distance
        specific_outer_meshes.sort(key=lambda x: x[1])
        specific_outer_mesh_names = [mesh[0] for mesh in specific_outer_meshes]
        
        # If we have enough specific outer meshes, use them
        if len(specific_outer_mesh_names) >= max_outer:
            print(f"Found {len(specific_outer_mesh_names)} specific outer meshes, using top {max_outer}")
            return specific_outer_mesh_names[:max_outer]
        
        # If we don't have enough specific outer meshes, find additional ones based on proximity
        print(f"Found {len(specific_outer_mesh_names)} specific outer meshes, looking for additional ones...")
        
        # Find all visible meshes within a certain distance
        additional_outer_meshes = []
        for obj in bpy.data.objects:
            if obj.type == 'MESH' and not obj.hide_viewport:
                # Skip if it's the target mesh or already in our specific list
                if obj.name == target_obj.name or obj.name in specific_outer_mesh_names:
                    continue
                    
                # Check side constraints if applicable
                if side and not self.is_mesh_on_side(obj.name, side):
                    continue
                
                # Skip meshes that match exclusion terms
                if exclusion_terms and any(term in obj.name.lower() for term in exclusion_terms):
                    print(f"  (INFO: Excluding mesh '{obj.name}' due to exclusion terms)")
                    continue
                
                # Check if mesh is in the same body region if we know the region
                if body_region != 'unknown':
                    obj_region = self._extract_region(obj.name)
                    if obj_region != 'unknown' and obj_region != body_region:
                        continue
                
                # Get object's center
                obj_center = obj.matrix_world @ obj.location
                
                # Calculate distance
                distance = (obj_center - target_center).length
                
                # Use a threshold based on the object's dimensions
                obj_size = max(obj.dimensions.x, obj.dimensions.y, obj.dimensions.z)
                target_size = max(target_obj.dimensions.x, target_obj.dimensions.y, target_obj.dimensions.z)
                threshold = (obj_size + target_size) * self.PAINTING_CONFIG.get('proximity_multiplier', 1.5)
                
                # Check if object is close enough
                if distance < threshold:
                    # Additional filtering: Check if the mesh name has some similarity to the body part
                    if body_part:
                        obj_name_lower = obj.name.lower()
                        body_part_words = body_part.split()
                        
                        # Check for direct word matches
                        has_match = False
                        for word in body_part_words:
                            if len(word) > 3 and word in obj_name_lower:
                                has_match = True
                                break
                        
                        if not has_match:
                            # Check for character similarity as a fallback
                            body_part_chars = set(body_part.replace(" ", ""))
                            obj_name_chars = set(obj_name_lower.replace(" ", ""))
                            similarity = len(body_part_chars.intersection(obj_name_chars)) / len(body_part_chars)
                            
                            if similarity < 0.3:  # Less than 30% character overlap
                                continue
                    
                    additional_outer_meshes.append((obj.name, distance))
        
        # Sort by distance (closest first)
        additional_outer_meshes.sort(key=lambda x: x[1])
        
        # Extract just the mesh names
        additional_outer_mesh_names = [mesh[0] for mesh in additional_outer_meshes]
        
        # Combine specific and additional outer meshes, prioritizing specific ones
        combined_outer_mesh_names = specific_outer_mesh_names + additional_outer_mesh_names
        
        # Limit number of outer meshes
        if len(combined_outer_mesh_names) > max_outer:
            combined_outer_mesh_names = combined_outer_mesh_names[:max_outer]
            
        print(f"Found {len(combined_outer_mesh_names)} total outer meshes for {muscle_name}")
        return combined_outer_mesh_names

    def process_injury_data(self, injury_data, use_xray=None):
        """
        Process injury data and apply visualizations with AI-enhanced mesh detection.
        
        Args:
            injury_data (list): List of injury data dictionaries
            use_xray (bool, optional): Parameter is kept for compatibility but ignored - 
                                      x-ray effect is always applied.
        
        Returns:
            bool: Success or failure
        """
        try:
            if not injury_data:
                print("No injury data provided")
                return True  # Return success even with no data
            
            print(f"Processing {len(injury_data)} injuries with AI-enhanced detection...")
            
            # ALWAYS apply x-ray effect, regardless of parameter
            apply_xray = True
            print("X-ray effect will ALWAYS be applied (forced to True)")
            
            # Reset any existing materials and processed body parts
            self.reset_visualization()
            self.processed_body_parts = set()  # Clear the set of processed body parts
            
            # First, apply x-ray effect (always enabled)
            print("Applying x-ray effect to model...")
            self.apply_xray_effect()
            
            # Deduplicate injury data based on body part and side
            unique_injuries = []
            processed_keys = set()
            
            for injury in injury_data:
                body_part = injury.get('bodyPart', '').lower()
                side = injury.get('side', '').lower()
                
                # Skip if missing required data
                if not body_part:
                    print("Skipping injury with missing body part")
                    continue
                    
                # Create a unique key for this injury
                injury_key = f"{body_part}_{side}"
                
                # Only add if not already processed
                if injury_key not in processed_keys:
                    unique_injuries.append(injury)
                    processed_keys.add(injury_key)
                else:
                    print(f"Skipping duplicate injury for {body_part} ({side})")
            
            print(f"Found {len(unique_injuries)} unique injuries after deduplication")
            
            # Process each unique injury
            successful_injuries = 0
            for injury in unique_injuries:
                try:
                    print(f"Processing injury: {injury}")
                    
                    # Process this specific injury
                    success = self._process_single_injury(injury)
                    
                    # Count successful applications
                    if success:
                        successful_injuries += 1
                    
                except Exception as e:
                    print(f"Error processing individual injury {injury}: {str(e)}")
                    traceback.print_exc()
                    # Continue with next injury
            
            print(f"Successfully processed {successful_injuries} out of {len(unique_injuries)} injuries.")
            
            # If we have the AI service, save any learned mappings
            if hasattr(self, 'ai_service') and self.ai_service:
                try:
                    if hasattr(self.ai_service, '_save_anatomical_knowledge'):
                        self.ai_service._save_anatomical_knowledge()
                        print("Saved updated anatomical knowledge to disk")
                except Exception as e:
                    print(f"Warning: Could not save AI knowledge base: {e}")
            
            return successful_injuries > 0
            
        except Exception as e:
            print(f"Error processing injury data: {str(e)}")
            traceback.print_exc()
            return False
    
    def _process_single_injury(self, injury):
        """
        Process a single injury and apply it to the model using AI-enhanced mesh detection.
        
        Args:
            injury: Dictionary containing injury data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Extract necessary data from injury dict
            body_part = injury.get('bodyPart', '').lower()
            side = injury.get('side', '').lower()
            injury_type = injury.get('injuryType', '').lower()
            severity = injury.get('severity', '').lower()
            status = injury.get('status', 'active').lower()
            
            print(f"Processing injury: {body_part} ({side}) - {injury_type} ({severity}) - {status}")
            
            # Skip if missing required data
            if not body_part:
                print("Skipping injury with missing body part")
                return False
            
            # Check for duplicate injuries - use a combination of body part and side as a unique key
            injury_key = f"{body_part}_{side}"
            if injury_key in self.processed_body_parts:
                print(f"Skipping duplicate injury for {body_part} ({side})")
                return True  # Return success to avoid counting as failure
            
            # Get appropriate color for this injury based on status
            if status == 'active':
                color = self.INJURY_COLORS['active']
                print(f"Using ACTIVE color (RED) for {body_part}")
            elif status == 'past':
                color = self.INJURY_COLORS['past']
                print(f"Using PAST color (ORANGE) for {body_part}")
            elif status == 'recovered':
                color = self.INJURY_COLORS['recovered']
                print(f"Using RECOVERED color (GREEN) for {body_part}")
            else:
                # Default to active if unknown status
                color = self.INJURY_COLORS['active']
                print(f"Using DEFAULT color for unknown status '{status}' for {body_part}")
            
            # Use our new exact mesh finding function
            exact_meshes = self._get_exact_injury_meshes(body_part, side)
            
            if not exact_meshes:
                print(f"No exact meshes found for {body_part} ({side})")
                
                # As a fallback, try to find any mesh that contains the body part name
                fallback_meshes = []
                for obj in bpy.data.objects:
                    if obj.type == 'MESH':
                        obj_name_lower = obj.name.lower()
                        if body_part in obj_name_lower and self.is_mesh_on_side(obj.name, side):
                            fallback_meshes.append(obj)
                
                if fallback_meshes:
                    print(f"Found {len(fallback_meshes)} fallback meshes containing '{body_part}'")
                    exact_meshes = fallback_meshes[:3]  # Limit to 3 fallback meshes
            
            # If still no meshes found, return failure
            if not exact_meshes:
                print(f"Could not find any meshes for body part: {body_part}")
                return False
            
            # Apply color to the exact meshes
            successful_applications = 0
            for mesh_obj in exact_meshes:
                print(f"Applying {status} color to exact mesh: {mesh_obj.name}")
                try:
                    if self.apply_injury_to_mesh(mesh_obj, color, status, injury_type, severity, is_inner=True):
                        successful_applications += 1
                except Exception as e:
                    print(f"Error applying injury to mesh {mesh_obj.name}: {e}")
            
            # Mark as processed
            self.processed_body_parts.add(injury_key)
            
            print(f"Successfully applied injury to {successful_applications} exact meshes")
            return successful_applications > 0
            
        except Exception as e:
            print(f"Error processing single injury: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def reset_visualization(self):
        """Reset all meshes to their original materials and visibility"""
        try:
            print("Resetting visualization...")
            
            # Restore original materials
            for obj_name, material in self.original_materials.items():
                obj = bpy.data.objects.get(obj_name)
                if obj and obj.type == 'MESH':
                    for i in range(len(obj.material_slots)):
                        obj.material_slots[i].material = material
            
            # Restore original visibility
            for obj_name, visibility in self.original_visibility.items():
                obj = bpy.data.objects.get(obj_name)
                if obj:
                    obj.hide_viewport = visibility
            
            print("Visualization reset complete")
            return True

        except Exception as e:
            print(f"ERROR: Failed to reset visualization: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def export_visualization(self, output_path):
        """Export the visualization to the specified output path."""
        try:
            # Create output directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Set up camera view
            self._setup_camera_view()
            
            # Configure render settings for better performance
            bpy.context.scene.render.resolution_x = 1280  # Lower resolution for better performance
            bpy.context.scene.render.resolution_y = 720   # Lower resolution for better performance
            bpy.context.scene.render.resolution_percentage = 100
            
            # Configure Workbench specific settings for rendering with minimal settings
            if bpy.context.scene.render.engine == 'BLENDER_WORKBENCH':
                if hasattr(bpy.context.scene, 'display'):
                    bpy.context.scene.display.shading.light = 'FLAT'  # Flat lighting is faster
                    bpy.context.scene.display.shading.color_type = 'MATERIAL'
                    bpy.context.scene.display.shading.show_shadows = False  # Disable shadows for better performance
                    bpy.context.scene.display.shading.show_cavity = False   # Disable cavity for better performance
                    bpy.context.scene.display.shading.show_object_outline = False  # Disable outline for better performance
                    bpy.context.scene.display.shading.show_specular_highlight = False  # Disable specular for better performance
            
            # Determine file format based on extension
            file_ext = os.path.splitext(output_path)[1].lower()
            
            # Set render parameters based on file format
            if file_ext in ['.png', '.jpg', '.jpeg', '.bmp']:
                bpy.context.scene.render.image_settings.file_format = 'PNG' if file_ext == '.png' else 'JPEG'
                bpy.context.scene.render.filepath = output_path
                bpy.ops.render.render(write_still=True)
                print(f"Visualization exported to {output_path}")
                return True
            else:
                print(f"Unsupported file format: {file_ext}")
                return False
            
        except Exception as e:
            print(f"Error exporting visualization: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def save_model(self, output_path):
        """Save the 3D model to the specified output path."""
        try:
            print(f"Saving model to: {output_path}")
            
            # Create output directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Determine file format based on extension
            file_ext = os.path.splitext(output_path)[1].lower()
            print(f"Detected file format: {file_ext}")
            
            # Select all mesh objects
            bpy.ops.object.select_all(action='DESELECT')
            mesh_count = 0
            for obj in bpy.context.scene.objects:
                if obj.type == 'MESH':
                    obj.select_set(True)
                    mesh_count += 1
            print(f"Selected {mesh_count} mesh objects for export")
            
            if file_ext == '.glb':
                # Export as GLB with simplified options
                print("Using GLB export format with simplified options")
                try:
                    # Try with minimal options first
                    bpy.ops.export_scene.gltf(
                        filepath=output_path,
                        use_selection=True,
                        export_format='GLB'
                    )
                    print("GLB export completed successfully")
                except Exception as e:
                    print(f"Error with GLB export: {e}")
                    return False
            elif file_ext == '.fbx':
                # Export as FBX with simplified options
                print("Using FBX export format")
                bpy.ops.export_scene.fbx(
                    filepath=output_path,
                    use_selection=True
                )
            elif file_ext == '.obj':
                # Export as OBJ with simplified options
                print("Using OBJ export format")
                bpy.ops.export_scene.obj(
                    filepath=output_path,
                    use_selection=True
                )
            else:
                print(f"Unsupported model format: {file_ext}")
                return False
            
            # Check if file was created
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path) / (1024 * 1024)  # Size in MB
                print(f"Model saved successfully to {output_path} ({file_size:.2f} MB)")
                return True
            else:
                print(f"Failed to save model: Output file not created at {output_path}")
                return False
            
        except Exception as e:
            print(f"Error saving model: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def _setup_camera_view(self):
        """Set up camera to view the entire model with minimal settings"""
        try:
            # Find the bounding box of all visible objects - simplified approach
            min_x, min_y, min_z = float('inf'), float('inf'), float('inf')
            max_x, max_y, max_z = float('-inf'), float('-inf'), float('-inf')
            
            # Only check a subset of objects for better performance
            visible_meshes = [obj for obj in bpy.data.objects if obj.type == 'MESH' and not obj.hide_viewport]
            
            # If there are too many objects, sample them for better performance
            if len(visible_meshes) > 100:
                import random
                visible_meshes = random.sample(visible_meshes, 100)
            
            for obj in visible_meshes:
                # Use object location and dimensions for faster calculation
                loc = obj.location
                dims = obj.dimensions
                
                # Calculate approximate bounds
                min_x = min(min_x, loc.x - dims.x/2)
                min_y = min(min_y, loc.y - dims.y/2)
                min_z = min(min_z, loc.z - dims.z/2)
                max_x = max(max_x, loc.x + dims.x/2)
                max_y = max(max_y, loc.y + dims.y/2)
                max_z = max(max_z, loc.z + dims.z/2)
            
            # Calculate center and dimensions
            center = mathutils.Vector(((min_x + max_x) / 2, (min_y + max_y) / 2, (min_z + max_z) / 2))
            dimensions = mathutils.Vector((max_x - min_x, max_y - min_y, max_z - min_z))
            
            # Position camera
            max_dim = max(dimensions.x, dimensions.y, dimensions.z)
            camera_distance = max_dim * 2.0  # Adjust this multiplier as needed
            
            # Position camera in front of the model
            self.camera.location = center + mathutils.Vector((0, -camera_distance, 0))
            
            # Point camera at the center - simplified calculation
            self.camera.rotation_euler = (math.radians(90), 0, 0)
            
            # Set camera parameters - minimal settings
            camera_data = self.camera.data
            camera_data.type = 'PERSP'
            camera_data.lens = 50  # 50mm lens
            
            # Position light - simplified setup
            self.light.location = center + mathutils.Vector((max_dim, -max_dim, max_dim))
            self.light.rotation_euler = (math.radians(45), 0, math.radians(45))
            
            print("Camera view set up successfully with minimal settings")
            
        except Exception as e:
            print(f"ERROR: Failed to set up camera view: {str(e)}")
            import traceback
            traceback.print_exc()

    def _get_mesh_names_for_body_part(self, body_part):
        """
        Get the specific mesh names for a given body part using AI-enhanced detection.
        Falls back to traditional mapping if AI service is unavailable.
        """
        try:
            body_part = body_part.lower()
            
            # Get all mesh names in the scene
            mesh_names = [obj.name for obj in bpy.data.objects if obj.type == 'MESH']
            
            # Try AI-based mesh detection first if available
            if hasattr(self, 'ai_service') and self.ai_service:
                try:
                    # Extract side information if present in the body part
                    side = None
                    if '_left' in body_part:
                        side = 'left'
                        body_part = body_part.replace('_left', '')
                    elif '_right' in body_part:
                        side = 'right'
                        body_part = body_part.replace('_right', '')
                    elif 'left_' in body_part:
                        side = 'left'
                        body_part = body_part.replace('left_', '')
                    elif 'right_' in body_part:
                        side = 'right'
                        body_part = body_part.replace('right_', '')
                    
                    # Use AI service to find matching meshes
                    ai_matches = self.ai_service.find_matching_meshes(body_part, mesh_names, side)
                    
                    if ai_matches:
                        print(f"AI found matches for {body_part} ({side}): {ai_matches}")
                        return list(set(ai_matches))
                except Exception as e:
                    print(f"AI-based mesh detection failed: {e}")
                    # Continue to traditional method if AI fails
            
            # Fall back to traditional mapping
            if body_part in self.BODY_PART_MESH_MAPPING:
                mesh_patterns = self.BODY_PART_MESH_MAPPING[body_part]
                print(f"Using traditional mapping for {body_part}: {mesh_patterns}")
                
                # Find matching meshes based on the patterns
                matching_meshes = []
                for pattern in mesh_patterns:
                    pattern_lower = pattern.lower()
                    for mesh_name in mesh_names:
                        if pattern_lower in mesh_name.lower():
                            matching_meshes.append(mesh_name)
                            print(f"Matched mesh {mesh_name} with pattern {pattern}")
                
                # Make sure we're not returning duplicate mesh names
                return list(set(matching_meshes))
            else:
                print(f"No mesh mapping found for body part: {body_part}")
                
                # Try a simple string matching as last resort
                fallback_matches = []
                for mesh_name in mesh_names:
                    if body_part in mesh_name.lower():
                        fallback_matches.append(mesh_name)
                
                if fallback_matches:
                    print(f"Found fallback matches for {body_part}: {fallback_matches}")
                    return fallback_matches
                
                return []
                
        except Exception as e:
            print(f"Error getting mesh names for body part {body_part}: {str(e)}")
            traceback.print_exc()
            return []
            
    def apply_injury_to_mesh(self, mesh_name, color, status, injury_type, severity, is_inner=False, is_outer=False):
        """
        Apply injury visualization to a specific mesh
        
        Args:
            mesh_name: Name of the mesh to apply injury to
            color: RGBA color tuple for the injury
            status: Status of the injury (active, past, recovered)
            injury_type: Type of injury
            severity: Severity of the injury
            is_inner: Whether this is an inner mesh
            is_outer: Whether this is an outer mesh
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get the mesh object
            mesh_obj = None
            if isinstance(mesh_name, str):
                mesh_obj = bpy.data.objects.get(mesh_name)
                if not mesh_obj:
                    print(f"Mesh not found: {mesh_name}")
                    return False
            else:
                # It's already an object
                mesh_obj = mesh_name
                mesh_name = mesh_obj.name
            
            # Additional check: Skip if mesh is too large (likely a general body part)
            # This helps prevent painting large, unrelated meshes
            if not is_inner and not is_outer:
                # Calculate volume as a rough estimate of size
                volume = mesh_obj.dimensions.x * mesh_obj.dimensions.y * mesh_obj.dimensions.z
                if volume > 100:  # Arbitrary threshold, adjust as needed
                    print(f"Skipping large mesh '{mesh_name}' with volume {volume:.2f}")
                    return False
            
            # Create a new material with the color for this status
            material_name = f"Injury_{status}_{mesh_name}"
            
            try:
                # Try to create a new material
                mat = bpy.data.materials.new(name=material_name)
                
                # Set material properties
                mat.use_nodes = False  # Use simple material for better compatibility
                
                # Adjust color based on whether it's an inner or outer mesh
                if is_inner:
                    # Inner meshes should be fully visible with injury color
                    alpha_multiplier = self.PAINTING_CONFIG.get('inner_mesh_alpha_multiplier', 1.0)
                    print(f"Using inner mesh alpha multiplier: {alpha_multiplier} for '{mesh_name}'")
                elif is_outer:
                    # Outer meshes should be transparent
                    alpha_multiplier = self.PAINTING_CONFIG.get('outer_mesh_alpha_multiplier', 0.0)
                    print(f"Using outer mesh alpha multiplier: {alpha_multiplier} for '{mesh_name}'")
                else:
                    # Default case
                    alpha_multiplier = 1.0
                
                # Apply the alpha multiplier to the color
                adjusted_color = (color[0], color[1], color[2], color[3] * alpha_multiplier)
                mat.diffuse_color = adjusted_color
                
                # Configure material for correct display
                mat.blend_method = self.PAINTING_CONFIG.get('blend_method', 'HASHED')
                mat.shadow_method = 'NONE'
                mat.use_backface_culling = False
                
                # Assign the material to the mesh
                try:
                    # First check if it already has materials
                    if len(mesh_obj.material_slots) == 0:
                        mesh_obj.data.materials.append(mat)
                    else:
                        # Replace the first material
                        mesh_obj.material_slots[0].material = mat
                except Exception as material_error:
                    print(f"Error applying material to mesh {mesh_name}: {str(material_error)}")
                    # Try alternative approach
                    try:
                        # Clear all materials and add new one
                        mesh_obj.data.materials.clear()
                        mesh_obj.data.materials.append(mat)
                        print(f"Successfully applied material using alternative method")
                    except Exception as alt_error:
                        print(f"Alternative material application also failed: {str(alt_error)}")
                        return False
                    
                print(f"Applied {status} injury material to {mesh_name}")
                return True
                
            except Exception as material_error:
                print(f"Error creating material for mesh {mesh_name}: {str(material_error)}")
                
                # Try a simpler approach as a fallback
                try:
                    # Create a basic material without any special properties
                    basic_mat = bpy.data.materials.new(name=f"Basic_{material_name}")
                    basic_mat.diffuse_color = color
                    
                    # Assign the basic material
                    if len(mesh_obj.material_slots) == 0:
                        mesh_obj.data.materials.append(basic_mat)
                    else:
                        mesh_obj.material_slots[0].material = basic_mat
                    
                    print(f"Applied basic material to {mesh_name} as fallback")
                    return True
                except Exception as basic_error:
                    print(f"Basic material fallback also failed: {str(basic_error)}")
                    return False
                
        except Exception as e:
            print(f"Error applying injury to mesh {mesh_name}: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def apply_xray_effect(self):
        """Apply x-ray effect to the model, making all meshes semi-transparent with a blueish glow."""
        print("Applying x-ray effect to model...")
        
        # Create the x-ray material
        xray_material = self.create_xray_material()
        
        # Store original materials for all meshes if not already stored
        for obj in bpy.data.objects:
            if obj.type == 'MESH' and obj.name not in self.original_materials:
                self.original_materials[obj.name] = [slot.material for slot in obj.material_slots]
                self.original_visibility[obj.name] = obj.hide_viewport
        
        # Apply x-ray material to all non-hidden meshes
        meshes_affected = 0
        for obj in bpy.data.objects:
            if obj.type == 'MESH' and not obj.hide_viewport:
                # Skip specific outer meshes that should remain transparent
                skip_mesh = False
                for outer_mesh in self.OUTER_MESHES:
                    if outer_mesh.lower() in obj.name.lower():
                        skip_mesh = True
                        break
                
                if skip_mesh:
                    continue
                
                # Apply the x-ray material to all material slots
                if obj.data.materials:
                    for i in range(len(obj.data.materials)):
                        obj.data.materials[i] = xray_material
                else:
                    # No existing materials, add a new one
                    obj.data.materials.append(xray_material)
                
                meshes_affected += 1
        
        print(f"Applied x-ray effect to {meshes_affected} meshes")
        return True
    
    def create_xray_material(self):
        """Create a semi-transparent x-ray material with a blueish glow."""
        # Create a unique material name with timestamp to avoid conflicts
        material_name = f"XRay_Material_{time.time()}"
        
        # Get x-ray settings from config
        xray_color = self.PAINTING_CONFIG.get('xray_color', (0.8, 0.9, 1.0, 1.0))
        xray_opacity = self.PAINTING_CONFIG.get('xray_opacity', 1.0)
        emission_strength = self.PAINTING_CONFIG.get('xray_emission_strength', 0.8)
        
        # Create the material
        material = bpy.data.materials.new(name=material_name)
        material.use_nodes = False  # Use simpler material model for better performance
        
        # Set material properties
        material.diffuse_color = (xray_color[0], xray_color[1], xray_color[2], xray_opacity)
        material.roughness = self.PAINTING_CONFIG.get('roughness', 0.9)
        
        # Set transparency options
        material.blend_method = 'BLEND'
        material.shadow_method = 'NONE'
        material.use_backface_culling = False
        
        print(f"Created x-ray material: {material_name}")
        return material

    def _filter_irrelevant_meshes(self, meshes, body_part):
        """
        Filter out irrelevant meshes based on body part.
        
        Args:
            meshes: List of mesh names to filter
            body_part: Body part to filter for
            
        Returns:
            List of filtered mesh names
        """
        body_part_lower = body_part.lower()
        filtered_meshes = []
        
        # Define exclusion terms based on body part
        exclusion_terms = []
        if 'foot' in body_part_lower or 'ankle' in body_part_lower:
            exclusion_terms = ['hand', 'palmar', 'pollicis', 'carpal', 'carpus', 'metacarpal']
            print(f"Filtering out hand-related meshes for foot/ankle body part")
        elif 'hand' in body_part_lower or 'wrist' in body_part_lower:
            exclusion_terms = ['foot', 'plantar', 'hallucis', 'tarsal', 'tarsus', 'metatarsal']
            print(f"Filtering out foot-related meshes for hand/wrist body part")
        
        # Filter meshes
        for mesh in meshes:
            mesh_lower = mesh.lower()
            if exclusion_terms and any(term in mesh_lower for term in exclusion_terms):
                print(f"  (INFO: Filtering out irrelevant mesh '{mesh}' for body part '{body_part}')")
                continue
            filtered_meshes.append(mesh)
        
        print(f"Filtered {len(meshes) - len(filtered_meshes)} irrelevant meshes for body part '{body_part}'")
        return filtered_meshes

    def _get_exact_injury_meshes(self, body_part, side):
        """
        Get only the exact meshes that correspond to the injured body part.
        This is a much more selective approach than the previous methods.
        
        Args:
            body_part: The body part that is injured
            side: The side of the injury (left, right, bilateral)
            
        Returns:
            List of mesh objects that exactly match the injured body part
        """
        print(f"Finding exact meshes for {body_part} ({side} side)...")
        
        # Normalize body part name
        body_part = body_part.lower().strip()
        
        # Create a mapping of common body parts to their exact mesh names
        body_part_to_mesh_map = {
            'shoulder': [
                'Deltoid', 'Supraspinatus', 'Infraspinatus', 'Teres minor', 
                'Subscapularis', 'Acromial part of deltoid muscle'
            ],
            'arm': [
                'Biceps brachii', 'Triceps brachii', 'Brachialis', 'Brachioradialis'
            ],
            'foot': [
                'Extensor digitorum brevis', 'Extensor hallucis brevis', 'Abductor hallucis',
                'Flexor digitorum brevis', 'Abductor digiti minimi of foot'
            ],
            'ankle': [
                'Tibialis anterior', 'Tibialis posterior', 'Fibularis longus', 
                'Fibularis brevis', 'Calcaneal tendon'
            ],
            'knee': [
                'Rectus femoris', 'Vastus lateralis', 'Vastus medialis', 'Vastus intermedius',
                'Patellar retinaculum'
            ],
            'wrist': [
                'Flexor carpi radialis', 'Flexor carpi ulnaris', 'Extensor carpi radialis',
                'Extensor carpi ulnaris'
            ],
            'hand': [
                'Abductor pollicis brevis', 'Opponens pollicis', 'Flexor pollicis brevis',
                'Adductor pollicis', 'Abductor digiti minimi of hand'
            ],
            'neck': [
                'Sternocleidomastoid', 'Trapezius', 'Longus colli', 'Longus capitis'
            ],
            'back': [
                'Erector spinae', 'Multifidus', 'Quadratus lumborum', 'Latissimus dorsi'
            ],
            'hip': [
                'Gluteus maximus', 'Gluteus medius', 'Gluteus minimus', 'Piriformis',
                'Tensor fasciae latae'
            ]
        }
        
        # Get the list of mesh names for this body part
        target_mesh_patterns = []
        
        # First check for exact matches in our mapping
        if body_part in body_part_to_mesh_map:
            target_mesh_patterns = body_part_to_mesh_map[body_part]
        else:
            # If no exact match, check for partial matches
            for key, patterns in body_part_to_mesh_map.items():
                if key in body_part or body_part in key:
                    target_mesh_patterns = patterns
                    break
        
        # If still no matches, use the body part name itself as a pattern
        if not target_mesh_patterns:
            # Split the body part into words and use words with 4+ characters
            words = body_part.split()
            target_mesh_patterns = [word for word in words if len(word) >= 4]
            
            if not target_mesh_patterns:
                # If still no patterns, use the whole body part name
                target_mesh_patterns = [body_part]
        
        print(f"Using mesh patterns for {body_part}: {target_mesh_patterns}")
        
        # Find meshes that match our patterns
        exact_meshes = []
        for obj in bpy.data.objects:
            if obj.type != 'MESH':
                continue
                
            obj_name_lower = obj.name.lower()
            
            # Check if this mesh matches any of our patterns
            for pattern in target_mesh_patterns:
                pattern_lower = pattern.lower()
                if pattern_lower in obj_name_lower:
                    # Check if it's on the correct side
                    if self.is_mesh_on_side(obj.name, side):
                        print(f"  (INFO: Found exact match '{obj.name}' for pattern '{pattern}')")
                        exact_meshes.append(obj)
                        break
        
        # If we found too many meshes, limit to the most relevant ones
        if len(exact_meshes) > 5:
            print(f"  (INFO: Found {len(exact_meshes)} matches, limiting to most relevant)")
            
            # Score each mesh based on how closely it matches the body part
            scored_meshes = []
            for mesh in exact_meshes:
                score = 0
                mesh_name_lower = mesh.name.lower()
                
                # Exact body part name in mesh name gets highest score
                if body_part in mesh_name_lower:
                    score += 10
                
                # Each pattern match adds to the score
                for pattern in target_mesh_patterns:
                    if pattern.lower() in mesh_name_lower:
                        score += 5
                
                # Shorter names are likely more specific
                score -= len(mesh_name_lower) * 0.1
                
                scored_meshes.append((mesh, score))
            
            # Sort by score (highest first)
            scored_meshes.sort(key=lambda x: x[1], reverse=True)
            
            # Take the top 5
            exact_meshes = [mesh for mesh, _ in scored_meshes[:5]]
        
        print(f"Found {len(exact_meshes)} exact meshes for {body_part}")
        return exact_meshes

# Example usage
if __name__ == "__main__":
    try:
        # Get command line arguments
        script_args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
        
        if len(script_args) < 3:
            print("Usage: blender --background --python paint_fbx_model.py -- <fbx_path> <injury_json_path> <output_path> [use_xray]")
            print("  use_xray: Optional parameter. Can be 'true' or 'false' to override config")
            sys.exit(1)
            
        # Extract required arguments
        fbx_path = script_args[0]
        injury_json_path = script_args[1]
        output_path = script_args[2]
        
        # Check for optional x-ray parameter with robust error handling
        use_xray = None  # Default to None to use config setting
        if len(script_args) > 3:
            try:
                use_xray_arg = script_args[3].lower()
                if use_xray_arg in ['true', 'false']:
                    use_xray = (use_xray_arg == 'true')
                    print(f"Command line override for use_xray: {use_xray}")
                else:
                    print(f"Invalid use_xray value '{script_args[3]}'. Must be 'true' or 'false'. Using config default.")
            except Exception as e:
                print(f"Error parsing use_xray parameter: {e}")
                print("Using default from config")
        
        print(f"FBX Path: {fbx_path}")
        print(f"Injury JSON Path: {injury_json_path}")
        print(f"Output Path: {output_path}")
        print(f"Use X-ray: {use_xray if use_xray is not None else 'Using config default'}")
        
        # Check if files exist
        if not os.path.exists(fbx_path):
            print(f"ERROR: FBX file not found: {fbx_path}")
            sys.exit(1)
            
        if not os.path.exists(injury_json_path):
            print(f"ERROR: Injury JSON file not found: {injury_json_path}")
            sys.exit(1)
        
        # Load injury data with error handling
        try:
            with open(injury_json_path, 'r') as f:
                injury_data = json.load(f)
        except Exception as e:
            print(f"ERROR: Failed to load injury data from {injury_json_path}: {e}")
            sys.exit(1)
            
        if not isinstance(injury_data, list):
            print(f"WARNING: Injury data is not a list. Converting...")
            if injury_data is None:
                injury_data = []
            else:
                injury_data = [injury_data]
        
        # Create visualizer
        visualizer = InjuryVisualizer(fbx_path)
        
        # Process injury data
        if not visualizer.process_injury_data(injury_data, use_xray):
            print("ERROR: Failed to process injury data")
            sys.exit(1)
        
        # Determine output type based on file extension
        file_ext = os.path.splitext(output_path)[1].lower()
        
        export_success = False
        if file_ext in ['.png', '.jpg', '.jpeg', '.bmp']:
            # Export as image
            print(f"Exporting as image: {output_path}")
            export_success = visualizer.export_visualization(output_path)
        else:
            # Export as 3D model (GLB, FBX, OBJ)
            print(f"Exporting as 3D model: {output_path}")
            export_success = visualizer.save_model(output_path)
        
        if export_success:
            print("Visualization complete and exported successfully")
            sys.exit(0)
        else:
            print("ERROR: Failed to export visualization")
            sys.exit(1)
        
    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 