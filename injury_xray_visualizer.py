"""
Injury X-Ray Visualizer - Advanced visualization system for medical injury models
Creates dual-layer visualization with X-ray effect to see through outer tissues to injuries

Based on techniques used in medical visualization software and anatomy applications
"""

import os
import sys
import json
import time
import tempfile
import subprocess
from pathlib import Path

class InjuryXRayVisualizer:
    def __init__(self, base_fbx_path=None, output_dir=None):
        """Initialize the X-Ray visualizer with paths"""
        # Set up paths
        self.script_dir = Path(__file__).resolve().parent
        
        if base_fbx_path:
            self.fbx_path = Path(base_fbx_path)
        else:
            self.models_dir = self.script_dir / 'models' / 'z-anatomy'
            self.fbx_path = self.models_dir / 'Muscular.fbx'
        
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = self.script_dir / 'models' / 'z-anatomy' / 'output'
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
    
    def create_xray_visualization(self, injury_data):
        """
        Create an X-ray style visualization that makes injuries visible through outer tissues
        
        Args:
            injury_data (list): List of injury dictionaries with bodyPart, side, status, etc.
            
        Returns:
            str: Path to the output GLB file with X-ray visualization
        """
        print(f"Creating X-ray injury visualization with {len(injury_data)} injuries")
        
        # Generate unique output path
        output_path = self.output_dir / f"xray_injuries_{int(time.time())}.glb"
        
        # Create the Blender script content
        script_content = self._generate_blender_script(injury_data, output_path)
        
        # Execute the script with Blender
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Create a temporary Python script for Blender
                script_path = Path(temp_dir) / "xray_injuries.py"
                
                # Write the script to the temporary file
                with open(script_path, 'w') as f:
                    f.write(script_content)
                
                # Find Blender executable
                blender_path = self._find_blender_executable()
                
                # Run Blender with the script
                cmd = [
                    blender_path,
                    '--background',
                    '--python', str(script_path),
                    '-noaudio'
                ]
                
                print(f"Running command: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                # Print output
                print("Blender script output:")
                print(result.stdout)
                
                if result.stderr:
                    print("Blender script errors:")
                    print(result.stderr)
                
                # Check if output file was created
                if not os.path.exists(output_path):
                    raise Exception(f"Failed to create output file at {output_path}")
                
                print(f"Successfully created X-ray visualization at: {output_path}")
                return str(output_path)
                
        except Exception as e:
            print(f"Error creating X-ray visualization: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    def _find_blender_executable(self):
        """Find the Blender executable path"""
        blender_path = 'blender'  # Default to PATH
        
        common_paths = [
            r'C:\Program Files\Blender Foundation\Blender 3.6',
            r'C:\Program Files\Blender Foundation\Blender',
            '/usr/bin/blender',
            '/Applications/Blender.app/Contents/MacOS/Blender'
        ]
        
        for path in common_paths:
            potential_path = os.path.join(path, 'blender.exe' if os.name == 'nt' else 'blender')
            if os.path.exists(potential_path):
                blender_path = potential_path
                break
        
        print(f"Using Blender at: {blender_path}")
        return blender_path
    
    def _generate_blender_script(self, injury_data, output_path):
        """Generate the Blender script for X-ray visualization"""
        return f"""
import bpy
import sys
import os
import math
import json
from mathutils import Vector

# Set paths and data
fbx_path = r"{str(self.fbx_path)}"
output_path = r"{str(output_path)}"
injury_data = {json.dumps(injury_data)}

print(f"Processing FBX: {{fbx_path}}")
print(f"Will export to: {{output_path}}")
print(f"Injuries to visualize: {{injury_data}}")

# Clear existing scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Import the FBX
bpy.ops.import_scene.fbx(filepath=fbx_path)

# Define outer mesh patterns (these will be made special transparent)
outer_mesh_patterns = [
    'fascia', 'Fascia', 'aponeurosis', 'Aponeurosis', 'retinaculum', 'Retinaculum',
    'bursa', 'Bursa', 'Platysma', 'platysma', 'Epicranial', 'epicranial',
    'Frontalis', 'frontalis', 'Temporoparietalis', 'temporoparietalis',
    'Zygomaticus', 'zygomaticus', 'Risorius', 'risorius', 'oris', 'Oris',
    'Masseteric', 'masseteric', 'Depressor', 'depressor', 'Buchinator', 'buchinator',
    'Superficial', 'superficial', 'OCcipitalis', 'occipitalis', 'Procerus', 'procerus',
    'Dorsa', 'dorsa', 'Ilitibial', 'ilitibial', 'Popliteal', 'popliteal',
    'Crucal', 'crucal', 'Subcutaneous', 'subcutaneous', 'Deltoid_fascia', 'Brachial_fascia',
    'Antebrachial_fascia', 'Palmar_aponeurosis', 'Pectoral_fascia', 'Investing_abdominal_fascia'
]

# Define body part to mesh patterns mapping
body_part_mesh_mapping = {{
    'biceps': ['Biceps', 'biceps', 'brachii', 'Upper arm', 'upper arm', 'Brachialis'],
    'triceps': ['Triceps', 'triceps', 'brachii', 'Upper arm', 'upper arm'],
    'quadriceps': ['Quadriceps', 'quadriceps', 'Rectus femoris', 'Vastus', 'Thigh', 'thigh'],
    'hamstring': ['Hamstring', 'hamstring', 'Biceps femoris', 'Semitendinosus', 'Semimembranosus'],
    'calf': ['Gastrocnemius', 'gastrocnemius', 'Soleus', 'soleus', 'Calf', 'calf', 'lower leg'],
    'shoulder': ['Deltoid', 'deltoid', 'Supraspinatus', 'Infraspinatus', 'Teres', 'Shoulder', 'shoulder'],
    'thigh': ['Thigh', 'thigh', 'Quadriceps', 'Hamstring', 'Vastus', 'Rectus femoris'],
    'neck': ['Neck', 'neck', 'Sternocleidomastoid', 'Trapezius'],
    'back': ['Back', 'back', 'Latissimus', 'Trapezius', 'Erector'],
    'chest': ['Chest', 'chest', 'Pectoralis', 'pectoralis'],
    'abdomen': ['Abdomen', 'abdomen', 'Rectus abdominis', 'Oblique', 'abs', 'Abs']
}}

# Collect all meshes
all_meshes = []
outer_meshes = []
other_meshes = []

for obj in bpy.data.objects:
    if obj.type == 'MESH':
        # Check if it's an outer mesh
        is_outer = any(pattern in obj.name for pattern in outer_mesh_patterns)
        
        if is_outer:
            outer_meshes.append(obj)
        else:
            other_meshes.append(obj)
        
        all_meshes.append(obj)

print(f"Found {{len(all_meshes)}} total meshes")
print(f"Found {{len(outer_meshes)}} outer meshes")
print(f"Found {{len(other_meshes)}} other meshes")

# Function to determine if mesh relates to an injury
def is_injury_related(obj, injury):
    body_part = injury.get('bodyPart', '').lower()
    side = injury.get('side', '').lower()
    
    # Skip if no body part specified
    if not body_part:
        return False
    
    # Get mesh patterns for this body part
    patterns = body_part_mesh_mapping.get(body_part, [body_part])
    obj_name_lower = obj.name.lower()
    
    # Check if mesh name contains any pattern
    matches_body_part = any(pattern.lower() in obj_name_lower for pattern in patterns)
    
    # Check if side matches
    if side == 'left':
        matches_side = obj.name.endswith('.l') or 'left' in obj_name_lower
    elif side == 'right':
        matches_side = obj.name.endswith('.r') or 'right' in obj_name_lower
    else:
        matches_side = True
    
    return matches_body_part and matches_side

# Group injuries by related mesh regions
injury_regions = []

for injury in injury_data:
    related_meshes = [obj for obj in other_meshes if is_injury_related(obj, injury)]
    
    if related_meshes:
        # Calculate the center of these meshes
        center = Vector((0, 0, 0))
        count = 0
        
        for obj in related_meshes:
            # Get object's world position
            center += obj.matrix_world.translation
            count += 1
        
        if count > 0:
            center = center / count
            
            # Calculate radius to encompass all related meshes
            radius = 0
            for obj in related_meshes:
                distance = (obj.matrix_world.translation - center).length
                size = max(obj.dimensions.x, obj.dimensions.y, obj.dimensions.z)
                radius = max(radius, distance + size)
            
            # Add a buffer to the radius
            radius *= 1.5
            
            # Store the region data
            region = {{
                'injury': injury,
                'center': center,
                'radius': radius,
                'meshes': related_meshes
            }}
            
            injury_regions.append(region)
            print(f"Created injury region for {{injury.get('bodyPart')}} with {{len(related_meshes)}} meshes, radius {{radius}}")

# Create materials based on injury status
materials = {{}}

def create_material(name, diffuse, emission=(0,0,0,1), emission_strength=0, alpha=1.0):
    '''Create a new material with specified properties optimized for app visibility'''
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    
    # Get material nodes
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    # Clear all nodes
    nodes.clear()
    
    # For injury materials (with emission), create a simpler material setup that will translate better to GLB
    if emission_strength > 0:
        # Create an Emission shader for strong colors that will be visible in the app
        emission_node = nodes.new('ShaderNodeEmission')
        emission_node.inputs['Color'].default_value = emission
        emission_node.inputs['Strength'].default_value = emission_strength
        emission_node.location = (0, 100)
        
        # Create a Diffuse BSDF for base color
        diffuse_node = nodes.new('ShaderNodeBsdfDiffuse')
        diffuse_node.inputs['Color'].default_value = diffuse
        diffuse_node.inputs['Roughness'].default_value = 0.5
        diffuse_node.location = (0, -100)
        
        # Create a Mix Shader to combine emission and diffuse
        mix_node = nodes.new('ShaderNodeMixShader')
        mix_node.inputs[0].default_value = 0.8  # 80% emission, 20% diffuse
        mix_node.location = (200, 0)
        
        # Create Material Output node
        output = nodes.new('ShaderNodeOutputMaterial')
        output.location = (400, 0)
        
        # Link the nodes
        links.new(emission_node.outputs[0], mix_node.inputs[1])
        links.new(diffuse_node.outputs[0], mix_node.inputs[2])
        links.new(mix_node.outputs[0], output.inputs['Surface'])
        
        # Add a strong unshaded color as fallback for renderers that don't support emission
        mat.diffuse_color = (diffuse[0], diffuse[1], diffuse[2], alpha)
    else:
        # For non-injury materials (like transparent outer meshes), use Principled BSDF
        principled = nodes.new('ShaderNodeBsdfPrincipled')
        principled.inputs['Base Color'].default_value = diffuse
        principled.inputs['Alpha'].default_value = alpha
        principled.inputs['Specular'].default_value = 0.3
        principled.inputs['Roughness'].default_value = 0.7
        principled.location = (0, 0)
        
        # Create Material Output node
        output = nodes.new('ShaderNodeOutputMaterial')
        output.location = (300, 0)
        
        # Link the nodes
        links.new(principled.outputs['BSDF'], output.inputs['Surface'])
    
    # Set material properties for transparency
    mat.blend_method = 'HASHED'  # Use hashed for better results
    mat.shadow_method = 'NONE'   # No shadows for transparent materials
    
    # For injury materials, ensure they're visible in the viewport
    if emission_strength > 0:
        # These settings help ensure the material is visible in different renderers
        mat.use_backface_culling = False
        mat.show_transparent_back = True
        
        # Set the diffuse color to match emission for fallback in simple renderers
        mat.diffuse_color = emission
    
    return mat

# Create materials for each injury status
active_material = create_material(
    "Injury_Active", 
    (1.0, 0.0, 0.0, 1.0),  # Red diffuse
    (1.0, 0.2, 0.2, 1.0),  # Red emission
    emission_strength=5.0
)

past_material = create_material(
    "Injury_Past", 
    (1.0, 0.5, 0.0, 1.0),  # Orange diffuse
    (1.0, 0.6, 0.2, 1.0),  # Orange emission
    emission_strength=4.0
)

recovered_material = create_material(
    "Injury_Recovered", 
    (0.0, 1.0, 0.0, 1.0),  # Green diffuse
    (0.2, 1.0, 0.2, 1.0),  # Green emission
    emission_strength=3.0
)

# Create special x-ray outer material that shows injury beneath
xray_outer_material = create_material(
    "XRay_Outer", 
    (0.95, 0.95, 0.95, 1.0),  # Near-white diffuse
    (0, 0, 0, 1.0),           # No emission
    emission_strength=0,
    alpha=0.1                  # Very transparent
)

# Apply materials to injured meshes
for injury in injury_data:
    status = injury.get('status', '').lower()
    
    # Select material based on status
    if status == 'active':
        material = active_material
    elif status == 'past':
        material = past_material
    elif status == 'recovered':
        material = recovered_material
    else:
        material = active_material  # Default to active
    
    # Find meshes related to this injury
    for obj in other_meshes:
        if is_injury_related(obj, injury):
            # Apply material to the mesh
            if obj.data.materials:
                obj.data.materials[0] = material
            else:
                obj.data.materials.append(material)
                
            print(f"Applied {{status}} material to {{obj.name}}")

# Apply x-ray material to outer meshes
for obj in outer_meshes:
    if obj.data.materials:
        obj.data.materials[0] = xray_outer_material
    else:
        obj.data.materials.append(xray_outer_material)
    
    print(f"Applied x-ray material to outer mesh {{obj.name}}")

# Set up lighting for better visualization
for obj in bpy.data.objects:
    if obj.type == 'LIGHT':
        bpy.data.objects.remove(obj)

# Create key light (main illumination)
key_light = bpy.data.lights.new(name="Key_Light", type='SUN')
key_light.energy = 5.0
key_light.specular_factor = 0.2  # Reduce specular reflections
key_light_obj = bpy.data.objects.new("Key_Light", key_light)
bpy.context.collection.objects.link(key_light_obj)
key_light_obj.rotation_euler = (math.radians(45), 0, math.radians(135))

# Create fill light (reduces shadows)
fill_light = bpy.data.lights.new(name="Fill_Light", type='SUN')
fill_light.energy = 3.0
fill_light.specular_factor = 0.0  # No specular for fill light
fill_light_obj = bpy.data.objects.new("Fill_Light", fill_light)
bpy.context.collection.objects.link(fill_light_obj)
fill_light_obj.rotation_euler = (math.radians(75), 0, math.radians(-90))

# Create rim light (highlights edges)
rim_light = bpy.data.lights.new(name="Rim_Light", type='SUN')
rim_light.energy = 4.0
rim_light.specular_factor = 0.1
rim_light_obj = bpy.data.objects.new("Rim_Light", rim_light)
bpy.context.collection.objects.link(rim_light_obj)
rim_light_obj.rotation_euler = (math.radians(-30), 0, math.radians(45))

# Set world background to dark blue for better contrast
world = bpy.context.scene.world
if not world:
    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
world.use_nodes = True
bg_node = world.node_tree.nodes['Background']
bg_node.inputs['Color'].default_value = (0.03, 0.05, 0.10, 1.0)

# Optimize material settings for GLB export
for mat in bpy.data.materials:
    if mat.blend_method == 'HASHED':
        # For GLB export, these settings work better
        mat.blend_method = 'BLEND'  # Switch to standard blend
        mat.use_backface_culling = False
        
        # Ensure principled BSDF node has correct transparency
        if mat.use_nodes:
            for node in mat.node_tree.nodes:
                if node.type == 'BSDF_PRINCIPLED':
                    # Ensure emission is properly set
                    if 'Injury_Active' in mat.name:
                        node.inputs['Emission'].default_value = (1.0, 0.2, 0.2, 1.0)
                        node.inputs['Emission Strength'].default_value = 5.0
                    elif 'Injury_Past' in mat.name:
                        node.inputs['Emission'].default_value = (1.0, 0.6, 0.2, 1.0)
                        node.inputs['Emission Strength'].default_value = 4.0
                    elif 'Injury_Recovered' in mat.name:
                        node.inputs['Emission'].default_value = (0.2, 1.0, 0.2, 1.0)
                        node.inputs['Emission Strength'].default_value = 3.0
                    elif 'XRay_Outer' in mat.name:
                        node.inputs['Alpha'].default_value = 0.1
                        node.inputs['Specular'].default_value = 0.0
                        node.inputs['Roughness'].default_value = 1.0

# Set up scene for better visibility
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                space.shading.type = 'MATERIAL'
                space.shading.use_scene_lights = True
                space.shading.use_scene_world = True

# Add better lighting for enhanced visibility
def setup_improved_lighting():
    # Remove existing lights
    for obj in bpy.data.objects:
        if obj.type == 'LIGHT':
            bpy.data.objects.remove(obj)
    
    # Create a key light (main light)
    bpy.ops.object.light_add(type='SUN', radius=1.0, location=(5, 5, 10))
    key_light = bpy.context.active_object
    key_light.name = 'Key_Light'
    key_light.data.energy = 2.0
    key_light.data.angle = 0.5
    
    # Create a fill light (softer, from opposite side)
    bpy.ops.object.light_add(type='SUN', radius=1.0, location=(-5, -3, 8))
    fill_light = bpy.context.active_object
    fill_light.name = 'Fill_Light'
    fill_light.data.energy = 1.0
    fill_light.data.angle = 1.0
    
    # Create a rim light (from behind to highlight edges)
    bpy.ops.object.light_add(type='SUN', radius=1.0, location=(0, -10, 0))
    rim_light = bpy.context.active_object
    rim_light.name = 'Rim_Light'
    rim_light.data.energy = 1.5
    rim_light.data.angle = 0.3
    
    # Add ambient light for overall scene brightness
    bpy.ops.object.light_add(type='AREA', radius=1.0, location=(0, 0, 10))
    ambient_light = bpy.context.active_object
    ambient_light.name = 'Ambient_Light'
    ambient_light.data.energy = 3.0
    ambient_light.data.size = 10.0

# Set up improved lighting
setup_improved_lighting()

# Configure render settings for better quality
bpy.context.scene.render.engine = 'BLENDER_EEVEE'
bpy.context.scene.eevee.use_bloom = True
bpy.context.scene.eevee.bloom_intensity = 0.1
bpy.context.scene.eevee.use_ssr = True
bpy.context.scene.eevee.use_ssr_refraction = True
bpy.context.scene.eevee.use_gtao = True
bpy.context.scene.eevee.gtao_distance = 0.2
bpy.context.scene.eevee.gtao_factor = 1.0

# Export to GLB
bpy.ops.export_scene.gltf(
    filepath=output_path,
    export_format='GLB',
    use_selection=False,
    export_apply=True,
    export_materials='EXPORT',
    export_colors=True,
    export_attributes=True,
    export_extras=True,
    export_yup=True,
    export_lights=True,
    export_cameras=True
)

print(f"Successfully exported X-ray visualization to: {{output_path}}")
"""
    
    def generate_optimal_visualizations(self, injury_data):
        """
        Generate multiple visualization versions for optimal viewing:
        1. X-ray version (semi-transparent outer layers)
        2. Cutaway version (outer layers removed)
        3. Standard version (original with enhanced colors)
        
        Returns all files as a dictionary
        """
        result = {}
        
        # 0. Enhanced X-ray + Painting visualization (new combined approach)
        try:
            enhanced_path = self.create_enhanced_visualization(injury_data)
            if enhanced_path:
                result['enhanced'] = enhanced_path
                print(f"Successfully created enhanced visualization with X-ray and injury painting at: {enhanced_path}")
        except Exception as e:
            print(f"Error creating enhanced visualization: {str(e)}")
        
        # 1. X-ray visualization (our main version)
        try:
            result['xray'] = self.create_xray_visualization(injury_data)
        except Exception as e:
            print(f"Error creating X-ray visualization: {str(e)}")
        
        # 2. Generate cutaway version (completely remove outer meshes)
        try:
            cutaway_path = self.output_dir / f"cutaway_injuries_{int(time.time())}.glb"
            cutaway_script = self._generate_cutaway_script(injury_data, cutaway_path)
            
            with tempfile.TemporaryDirectory() as temp_dir:
                script_path = Path(temp_dir) / "cutaway_injuries.py"
                with open(script_path, 'w') as f:
                    f.write(cutaway_script)
                
                cmd = [
                    self._find_blender_executable(),
                    '--background',
                    '--python', str(script_path),
                    '-noaudio'
                ]
                
                subprocess.run(cmd, capture_output=True, text=True)
                
                if os.path.exists(cutaway_path):
                    result['cutaway'] = str(cutaway_path)
        except Exception as e:
            print(f"Error creating cutaway visualization: {str(e)}")
        
        # Return all generated visualizations
        return result
    
    def _generate_cutaway_script(self, injury_data, output_path):
        """Generate a script to create a cutaway visualization (outer meshes removed)"""
        return f"""
import bpy
import sys
import os
import math

# Set paths and data
fbx_path = r"{str(self.fbx_path)}"
output_path = r"{str(output_path)}"
injury_data = {json.dumps(injury_data)}

print(f"Processing cutaway visualization: {{fbx_path}}")

# Clear existing scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Import the FBX
bpy.ops.import_scene.fbx(filepath=fbx_path)

# Define outer mesh patterns (these will be removed)
outer_mesh_patterns = [
    'fascia', 'Fascia', 'aponeurosis', 'Aponeurosis', 'retinaculum', 'Retinaculum',
    'bursa', 'Bursa', 'Platysma', 'platysma', 'Epicranial', 'epicranial',
    'Frontalis', 'frontalis', 'Temporoparietalis', 'temporoparietalis',
    'Zygomaticus', 'zygomaticus', 'Risorius', 'risorius', 'oris', 'Oris',
    'Masseteric', 'masseteric', 'Depressor', 'depressor', 'Buchinator', 'buchinator',
    'Superficial', 'superficial', 'OCcipitalis', 'occipitalis', 'Procerus', 'procerus',
    'Dorsa', 'dorsa', 'Ilitibial', 'ilitibial', 'Popliteal', 'popliteal',
    'Crucal', 'crucal', 'Subcutaneous', 'subcutaneous'
]

# Find and remove outer meshes
to_delete = []
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        if any(pattern in obj.name for pattern in outer_mesh_patterns):
            to_delete.append(obj)

print(f"Removing {{len(to_delete)}} outer meshes")
for obj in to_delete:
    bpy.data.objects.remove(obj)

# Create materials for each injury status
active_material = bpy.data.materials.new(name="Injury_Active")
active_material.use_nodes = True
active_nodes = active_material.node_tree.nodes
active_principled = active_nodes.get('Principled BSDF')
active_principled.inputs['Base Color'].default_value = (1.0, 0.0, 0.0, 1.0)  # Red
active_principled.inputs['Emission'].default_value = (1.0, 0.2, 0.2, 1.0)
active_principled.inputs['Emission Strength'].default_value = 3.0

past_material = bpy.data.materials.new(name="Injury_Past")
past_material.use_nodes = True
past_nodes = past_material.node_tree.nodes
past_principled = past_nodes.get('Principled BSDF')
past_principled.inputs['Base Color'].default_value = (1.0, 0.5, 0.0, 1.0)  # Orange
past_principled.inputs['Emission'].default_value = (1.0, 0.6, 0.2, 1.0)
past_principled.inputs['Emission Strength'].default_value = 2.0

recovered_material = bpy.data.materials.new(name="Injury_Recovered")
recovered_material.use_nodes = True
recovered_nodes = recovered_material.node_tree.nodes
recovered_principled = recovered_nodes.get('Principled BSDF')
recovered_principled.inputs['Base Color'].default_value = (0.0, 1.0, 0.0, 1.0)  # Green
recovered_principled.inputs['Emission'].default_value = (0.2, 1.0, 0.2, 1.0)
recovered_principled.inputs['Emission Strength'].default_value = 1.5

# Define body part to mesh patterns mapping
body_part_mesh_mapping = {{
    'biceps': ['Biceps', 'biceps', 'brachii', 'Upper arm', 'upper arm', 'Brachialis'],
    'triceps': ['Triceps', 'triceps', 'brachii', 'Upper arm', 'upper arm'],
    'quadriceps': ['Quadriceps', 'quadriceps', 'Rectus femoris', 'Vastus', 'Thigh', 'thigh'],
    'hamstring': ['Hamstring', 'hamstring', 'Biceps femoris', 'Semitendinosus', 'Semimembranosus'],
    'calf': ['Gastrocnemius', 'gastrocnemius', 'Soleus', 'soleus', 'Calf', 'calf'],
    'shoulder': ['Deltoid', 'deltoid', 'Supraspinatus', 'Infraspinatus', 'Teres', 'Shoulder', 'shoulder'],
    'thigh': ['Thigh', 'thigh', 'Quadriceps', 'Hamstring', 'Vastus', 'Rectus femoris']
}}

# Apply materials based on injuries
for injury in injury_data:
    body_part = injury.get('bodyPart', '').lower()
    side = injury.get('side', '').lower()
    status = injury.get('status', '').lower()
    
    # Get patterns for this body part
    patterns = body_part_mesh_mapping.get(body_part, [body_part])
    
    # Select material based on status
    if status == 'active':
        material = active_material
    elif status == 'past':
        material = past_material
    elif status == 'recovered':
        material = recovered_material
    else:
        material = active_material  # Default
    
    # Find and apply to matching meshes
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            obj_name_lower = obj.name.lower()
            
            # Check if mesh matches body part
            matches_body_part = any(pattern.lower() in obj_name_lower for pattern in patterns)
            
            # Check if side matches
            if side == 'left':
                matches_side = obj.name.endswith('.l') or 'left' in obj_name_lower
            elif side == 'right':
                matches_side = obj.name.endswith('.r') or 'right' in obj_name_lower
            else:
                matches_side = True
            
            if matches_body_part and matches_side:
                # Apply material
                if obj.data.materials:
                    obj.data.materials[0] = material
                else:
                    obj.data.materials.append(material)
                
                print(f"Applied {{status}} material to {{obj.name}}")

# Set up lighting
for obj in bpy.data.objects:
    if obj.type == 'LIGHT':
        bpy.data.objects.remove(obj)

# Create key light
key_light = bpy.data.lights.new(name="Key_Light", type='SUN')
key_light.energy = 4.0
key_light_obj = bpy.data.objects.new("Key_Light", key_light)
bpy.context.collection.objects.link(key_light_obj)
key_light_obj.rotation_euler = (math.radians(60), 0, math.radians(135))

# Create fill light
fill_light = bpy.data.lights.new(name="Fill_Light", type='SUN')
fill_light.energy = 2.0
fill_light_obj = bpy.data.objects.new("Fill_Light", fill_light)
bpy.context.collection.objects.link(fill_light_obj)
fill_light_obj.rotation_euler = (math.radians(75), 0, math.radians(-90))

# Set world background
world = bpy.context.scene.world
if not world:
    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
world.use_nodes = True
bg_node = world.node_tree.nodes['Background']
bg_node.inputs['Color'].default_value = (0.05, 0.08, 0.12, 1.0)  # Dark blue-gray

# Export to GLB
bpy.ops.export_scene.gltf(
    filepath=output_path,
    export_format='GLB',
    use_selection=False,
    export_apply=True,
    export_materials='EXPORT',
    export_colors=True,
    export_lights=True
)

print(f"Successfully exported cutaway visualization to: {{output_path}}")
"""

    def create_enhanced_visualization(self, injury_data):
        """
        Create a visualization that combines X-ray transparency with proper injury coloring
        based on injury status and severity - the best of both approaches.
        
        Args:
            injury_data (list): List of injury dictionaries with bodyPart, side, status, etc.
            
        Returns:
            str: Path to the output GLB file with enhanced visualization
        """
        print(f"Creating enhanced injury visualization (X-ray + Painting) with {len(injury_data)} injuries")
        
        # Generate unique output path
        output_path = self.output_dir / f"enhanced_injuries_{int(time.time())}.glb"
        
        # Generate the enhanced Blender script that combines X-ray and painting
        script = self._generate_enhanced_script(injury_data, output_path)
        
        # Create a temporary file to hold the script
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = Path(temp_dir) / "enhanced_injuries.py"
            with open(script_path, 'w') as f:
                f.write(script)
            
            # Find Blender executable
            blender_path = self._find_blender_executable()
            
            # Run Blender with the script
            print(f"Running Blender with script: {script_path}")
            try:
                subprocess.run([blender_path, "--background", "--python", str(script_path)], 
                              check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True)
                
                # Check if output was created
                if output_path.exists():
                    print(f"Successfully created enhanced visualization at: {output_path}")
                    return str(output_path)
                else:
                    print(f"Blender script ran but no output was created at: {output_path}")
                    return None
            except subprocess.CalledProcessError as e:
                print(f"Error running Blender script: {e.output}")
                print(f"Error details: {e.stderr}")
                raise
        
        return None
    
    def _generate_enhanced_script(self, injury_data, output_path):
        """Generate the Blender script for enhanced visualization that combines X-ray and painting"""
        return f"""
import bpy
import sys
import os
import math
import json
from mathutils import Vector

# Set paths and data
fbx_path = r"{str(self.fbx_path)}"
output_path = r"{str(output_path)}"
injury_data = {json.dumps(injury_data)}

print(f"Processing FBX: {{fbx_path}}")
print(f"Will export to: {{output_path}}")
print(f"Injuries to visualize: {{injury_data}}")

# Clear existing scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Import the FBX
bpy.ops.import_scene.fbx(filepath=fbx_path)

# Define outer mesh patterns (these will be made transparent)
outer_mesh_patterns = [
    'fascia', 'Fascia', 'aponeurosis', 'Aponeurosis', 'retinaculum', 'Retinaculum',
    'bursa', 'Bursa', 'Platysma', 'platysma', 'Epicranial', 'epicranial',
    'Frontalis', 'frontalis', 'Temporoparietalis', 'temporoparietalis',
    'Zygomaticus', 'zygomaticus', 'Risorius', 'risorius', 'oris', 'Oris',
    'Masseteric', 'masseteric', 'Depressor', 'depressor', 'Buchinator', 'buchinator',
    'Superficial', 'superficial', 'OCcipitalis', 'occipitalis', 'Procerus', 'procerus',
    'Dorsa', 'dorsa', 'Ilitibial', 'ilitibial', 'Popliteal', 'popliteal',
    'Crucal', 'crucal', 'Subcutaneous', 'subcutaneous', 'Deltoid_fascia', 'Brachial_fascia',
    'Antebrachial_fascia', 'Palmar_aponeurosis', 'Pectoral_fascia', 'Investing_abdominal_fascia'
]

# Define exact list of specific outer meshes that should always be made transparent
specific_outer_meshes = [
    'Deltoid_fascia', 'Deltoid_fascial', 'Deltoid_fasciar',
    'Brachial_fascia', 'Brachial_fascial', 'Brachial_fasciar',
    'Antebrachial_fascia', 'Antebrachial_fascial', 'Antebrachial_fasciar',
    'Palmar_aponeurosis', 'Palmar_aponeurosisl', 'Palmar_aponeurosisr',
    'Platysma', 'Platysmal', 'Platysmar',
    'Pectoral_fascia', 'Pectoral_fascial', 'Pectoral_fasciar',
    'Investing_abdominal_fascia', 'Investing_abdominal_fascial', 'Investing_abdominal_fasciar',
    'Fascia_lata', 'Fascia_latal', 'Fascia_latar',
    'Crural_fascia', 'Crural_fascial', 'Crural_fasciar',
    'subcutaneous_prepatellar_bursa', 'subcutaneous_prepatellar_bursal', 'subcutaneous_prepatellar_bursar',
    'subcutaneous_infrapatellar_bursa', 'subcutaneous_infrapatellar_bursal', 'subcutaneous_infrapatellar_bursar',
    'subcutaneous_bursa_of_tuberosity_of_tibia', 'subcutaneous_bursa_of_tuberosity_of_tibial', 'subcutaneous_bursa_of_tuberosity_of_tibiar',
    'superior_fibular_retinaculum', 'superior_fibular_retinaculuml', 'superior_fibular_retinaculumr',
    'Epicranial_aponeurosis', 'Epicranial_aponeurosisl', 'Epicranial_aponeurosisr',
    'Frontalis_muscle', 'Frontalis_musclel', 'Frontalis_muscler',
    'Temporoparietalis_muscle', 'Temporoparietalis_musclel', 'Temporoparietalis_muscler',
    'Zygomaticus_minor_muscle', 'Zygomaticus_minor_musclel', 'Zygomaticus_minor_muscler',
    'Risorius_muscle', 'Risorius_musclel', 'Risorius_muscler',
    'orbicularis_oris_muscle', 'orbicularis_oris_musclel', 'orbicularis_oris_muscler',
    'Masseteric_fascia', 'Masseteric_fascial', 'Masseteric_fasciar',
    'Depressor_anguli_oris', 'Depressor_anguli_orisl', 'Depressor_anguli_orisr',
    'Buchinator', 'Buchinatorl', 'Buchinatorr',
    'Zygomaticus_major_muscle', 'Zygomaticus_major_musclel', 'Zygomaticus_major_muscler',
    'Superficial_investing_cervical_fascia', 'Superficial_investing_cervical_fascial', 'Superficial_investing_cervical_fasciar',
    'OCcipitalis_muscle', 'OCcipitalis_musclel', 'OCcipitalis_muscler',
    'Procerus_muscle', 'Procerus_musclel', 'Procerus_muscler',
    'Dorsa_fascia_of_hand', 'Dorsa_fascia_of_handl', 'Dorsa_fascia_of_handr',
    'Ilitibial_tract', 'Ilitibial_tractl', 'Ilitibial_tractr',
    'Popliteal_fascia', 'Popliteal_fascial', 'Popliteal_fasciar',
    'Crucal_fascia', 'Crucal_fascial', 'Crucal_fasciar',
    'Subcutaneous_calcaneal_bursa', 'Subcutaneous_calcaneal_bursal', 'Subcutaneous_calcaneal_bursar'
]

# Define body part to mesh patterns mapping
body_part_mesh_mapping = {{
    'biceps': ['Biceps brachii muscle', 'Biceps brachii', 'Biceps', 'Bicep', 'Brachialis muscle', 'Brachialis', 'Upper arm', 'Arm muscles', 'Arm muscle'],
    'triceps': ['Triceps brachii muscle', 'Triceps brachii', 'Triceps', 'Upper arm', 'Arm muscles', 'Arm muscle'],
    'quadriceps': ['Quadriceps femoris muscle', 'Quadriceps femoris', 'Quadriceps', 'Quads', 'Quad', 'Rectus femoris muscle', 'Rectus femoris', 'Vastus lateralis muscle', 'Vastus lateralis', 'Vastus medialis muscle', 'Vastus medialis', 'Vastus intermedius muscle', 'Vastus intermedius', 'Thigh', 'Upper leg', 'Femoral'],
    'hamstring': ['Hamstring muscles', 'Hamstrings', 'Hamstring', 'Biceps femoris muscle', 'Biceps femoris', 'Semitendinosus muscle', 'Semitendinosus', 'Semimembranosus muscle', 'Semimembranosus'],
    'calf': ['Gastrocnemius muscle', 'Soleus muscle', 'Lateral head of gastrocnemius', 'Medial head of gastrocnemius', 'Calf', 'Lower leg'],
    'shoulder': ['Deltoid muscle', 'Supraspinatus muscle', 'Infraspinatus muscle', 'Teres minor muscle', 'Teres major muscle', 'Subscapularis muscle', 'Shoulder'],
    'thigh': ['Quadriceps femoris muscle', 'Quadriceps femoris', 'Quadriceps', 'Quads', 'Quad', 'Rectus femoris muscle', 'Rectus femoris', 'Vastus lateralis muscle', 'Vastus lateralis', 'Vastus medialis muscle', 'Vastus medialis', 'Vastus intermedius muscle', 'Vastus intermedius', 'Hamstring muscles', 'Hamstrings', 'Hamstring', 'Thigh', 'Upper leg', 'Femoral', 'Femur'],
    'neck': ['Neck', 'Cervical spine', 'Cervical', 'Trapezius muscle', 'Platysma', 'Sternocleidomastoid muscle', 'Sternocleidomastoid', 'Larynx'],
    'back': ['Back', 'Spine', 'Spinal', 'Vertebra', 'Vertebrae', 'Lumbar', 'Thoracic', 'Erector spinae', 'Latissimus', 'Trapezius'],
    'chest': ['Chest', 'Thorax', 'Thoracic', 'Pectoral', 'Pectoralis major', 'Pectoralis minor', 'Sternum', 'Rib'],
    'abdomen': ['Abdomen', 'Abdominal', 'Stomach', 'Belly', 'Rectus abdominis', 'Oblique', 'Transversus abdominis']
}}

# Define injury colors based on status - using much more saturated colors for app visibility
injury_colors = {{
    'active': (1.0, 0.0, 0.0, 1.0),     # Bright red for active injuries
    'past': (1.0, 0.4, 0.0, 1.0),       # Bright orange for past injuries
    'recovered': (0.0, 1.0, 0.0, 1.0),  # Bright green for recovered injuries
}}

# Define alpha values based on severity
severity_alpha = {{
    'mild': 1.0,      # Increased from 0.85 for better visibility
    'moderate': 1.0,  # Increased from 0.95 for better visibility
    'severe': 1.0
}}

# Collect all meshes
all_meshes = []
outer_meshes = []
other_meshes = []

for obj in bpy.data.objects:
    if obj.type == 'MESH':
        # Check if it's an outer mesh by pattern or in specific list
        is_outer = (any(pattern in obj.name for pattern in outer_mesh_patterns) or 
                   obj.name in specific_outer_meshes)
        
        if is_outer:
            outer_meshes.append(obj)
        else:
            other_meshes.append(obj)
        
        all_meshes.append(obj)

print(f"Found {{len(all_meshes)}} total meshes")
print(f"Found {{len(outer_meshes)}} outer meshes")
print(f"Found {{len(other_meshes)}} other meshes")

# Function to check side of object
def is_on_side(obj_name, side):
    if not side or side.lower() not in ['left', 'right']:
        return True  # No side specified, match all
        
    obj_name_lower = obj_name.lower()
    
    # Check for side indicators
    if side.lower() == 'left':
        return (obj_name.endswith('l') or 
                'left' in obj_name_lower or 
                'l_' in obj_name_lower or 
                '_l' in obj_name_lower or 
                '.l' in obj_name_lower)
    else:  # right
        return (obj_name.endswith('r') or 
                'right' in obj_name_lower or 
                'r_' in obj_name_lower or 
                '_r' in obj_name_lower or 
                '.r' in obj_name_lower)

# Function to get meshes for a body part
def get_meshes_for_body_part(body_part, side=None):
    if not body_part:
        return []
        
    body_part_lower = body_part.lower()
    
    # Get patterns for this body part
    patterns = body_part_mesh_mapping.get(body_part_lower, [body_part])
    
    # Find matching meshes
    matching_meshes = []
    for obj in other_meshes:
        obj_name_lower = obj.name.lower()
        
        # Check if mesh matches any pattern
        if any(pattern.lower() in obj_name_lower for pattern in patterns):
            # Check side if specified
            if side and not is_on_side(obj.name, side):
                continue
                
            matching_meshes.append(obj)
    
    return matching_meshes

# Function to export GLB with enhanced settings for better color preservation
def export_enhanced_glb(output_path):
    """Export GLB with settings optimized for color preservation"""
    print(f"Exporting enhanced GLB to: {output_path}")
    
    # First, ensure all materials have their viewport display color matching their shader color
    for mat in bpy.data.materials:
        if mat.node_tree and mat.node_tree.nodes:
            # Try to find emission or diffuse nodes
            for node in mat.node_tree.nodes:
                if node.type == 'EMISSION' and 'Color' in node.inputs:
                    # Set viewport color to match emission color
                    mat.diffuse_color = node.inputs['Color'].default_value
                    break
                elif node.type == 'BSDF_DIFFUSE' and 'Color' in node.inputs:
                    # Set viewport color to match diffuse color
                    mat.diffuse_color = node.inputs['Color'].default_value
                    break
    
    # Configure export settings for maximum compatibility
    export_settings = {
        'filepath': str(output_path),
        'export_format': 'GLB',
        'export_materials': 'EXPORT',
        'export_colors': True,
        'export_normals': True,
        'export_cameras': False,
        'export_extras': True,
        'export_lights': True,
        'export_animations': False,
        'export_texcoords': True,
        'export_attributes': True,
        'use_selection': False,
        'export_tangents': True,
        'export_yup': True
    }
    
    # Export with enhanced settings
    bpy.ops.export_scene.gltf(**export_settings)
    
    print(f"Successfully exported enhanced GLB to: {output_path}")
    return output_path

# Function to process injuries
def process_injuries(injury_data):
    """Process each injury and apply visualization effects"""
    if not injury_data:
        print("No injury data provided, skipping injury processing")
        return
        
    # Process each injury
    for injury in injury_data:
        body_part = injury.get('bodyPart', '')
        side = injury.get('side', '')
        status = injury.get('status', 'active')
        severity = injury.get('severity', 'moderate')
        
        print(f"Processing injury: {body_part} ({side}) - {status} {severity}")
        
        # Continue with injury processing logic here
        # ...

# Example usage if run directly
if __name__ == "__main__":
    # Sample injury data
    sample_injuries = [
        {
            "bodyPart": "biceps",
            "side": "right", 
            "injuryType": "strain",
            "severity": "moderate",
            "status": "active"
        },
        {
            "bodyPart": "quadriceps",
            "side": "left", 
            "injuryType": "bruise",
            "severity": "mild",
            "status": "past"
        }
    ]
    
    visualizer = InjuryXRayVisualizer()
    result = visualizer.create_xray_visualization(sample_injuries)
    print(f"X-ray visualization created at: {result}") 