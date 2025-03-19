import os
import json
from pathlib import Path
import subprocess
from medical_report_analysis import MedicalReportAnalysis
import tempfile
import shutil
import time
import math
import traceback
from typing import List, Dict, Any, Optional

# Try to import our AI service
try:
    from anatomical_ai_service import AnatomicalAIService
except ImportError:
    print("WARNING: AnatomicalAIService module not found. AI-enhanced mesh detection will not be available.")
    AnatomicalAIService = None

class InjuryVisualizationService:
    def __init__(self):
        self.script_dir = Path(__file__).resolve().parent
        self.models_dir = self.script_dir / 'models' / 'z-anatomy'
        self.fbx_path = self.models_dir / 'Muscular.fbx'
        self.output_dir = self.models_dir / 'output'
        
        # Initialize analyzers
        self.report_analyzer = MedicalReportAnalysis()
        
        # Initialize AI service for improved mesh detection if available
        try:
            # Check if the AnatomicalAIService is already initialized in app.py
            import sys
            if 'app' in sys.modules and hasattr(sys.modules['app'], 'anatomical_ai_service'):
                self.ai_service = sys.modules['app'].anatomical_ai_service
                print("Using AnatomicalAIService from app.py")
            elif AnatomicalAIService:
                # Try to get the Gemini API key from environment
                gemini_api_key = os.environ.get('GEMINI_API_KEY')
                if gemini_api_key:
                    self.ai_service = AnatomicalAIService(
                        api_key=gemini_api_key, 
                        use_local_fallback=True,
                        api_type="gemini"
                    )
                    print(f"Initialized AnatomicalAIService with Gemini API for enhanced mesh detection")
                else:
                    self.ai_service = AnatomicalAIService(use_local_fallback=True)
                    print("Initialized AnatomicalAIService with local fallback only (no Gemini API key found)")
            else:
                self.ai_service = None
        except Exception as e:
            print(f"WARNING: Could not initialize AnatomicalAIService: {e}")
            self.ai_service = None
        
        # Create necessary directories
        os.makedirs(self.models_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Check if the base FBX model exists
        if not os.path.exists(self.fbx_path):
            print(f"Base FBX model not found at: {self.fbx_path}")
            # Copy from a backup or download from a source
            try:
                # Create a default FBX file for testing
                default_fbx_path = self.script_dir / 'default_model.fbx'
                if os.path.exists(default_fbx_path):
                    shutil.copy2(default_fbx_path, self.fbx_path)
                    print(f"Copied default model to: {self.fbx_path}")
                else:
                    raise FileNotFoundError(f"Base FBX model not found at: {self.fbx_path}")
            except Exception as e:
                print(f"Error setting up base model: {e}")
                raise
        
        # Map common body part terms to standardized names
        self.body_part_mapping = {
            # Upper body
            'upper arm': 'upper arm',
            'bicep': 'biceps',  # Standardize to plural form
            'biceps': 'biceps',
            'tricep': 'triceps',  # Standardize to plural form
            'triceps': 'triceps',
            'shoulder': 'shoulder',
            'deltoid': 'shoulder',
            'chest': 'chest',
            'pectoral': 'chest',
            'back': 'back',
            'spine': 'back',
            'abdomen': 'abdomen',
            'abs': 'abdomen',
            'core': 'abdomen',
            
            # Lower body
            'thigh': 'thigh',
            'quadriceps': 'thigh',
            'quadricep': 'thigh',
            'quad': 'thigh',
            'quads': 'thigh',
            'upper leg': 'thigh',
            'hamstring': 'thigh',
            'knee': 'knee',
            'calf': 'calf',
            'gastrocnemius': 'calf',
            'lower leg': 'calf',
            'ankle': 'ankle',
            'foot': 'foot'
        }
        
        # Load additional anatomical knowledge if available
        self.load_anatomical_knowledge()
    
    def load_anatomical_knowledge(self):
        """Load additional anatomical knowledge from file if available"""
        try:
            knowledge_path = self.script_dir / 'anatomical_knowledge.json'
            if os.path.exists(knowledge_path):
                with open(knowledge_path, 'r') as f:
                    knowledge = json.load(f)
                
                # Update body part mapping with synonyms
                if 'synonyms' in knowledge:
                    for main_term, synonyms in knowledge['synonyms'].items():
                        for synonym in synonyms:
                            if synonym not in self.body_part_mapping:
                                self.body_part_mapping[synonym] = main_term
                
                print(f"Loaded additional anatomical knowledge with {len(knowledge.get('synonyms', {}))} terms")
                
                # Update AI service knowledge if available
                if hasattr(self, 'ai_service') and self.ai_service and hasattr(self.ai_service, 'expand_knowledge_base'):
                    self.ai_service.expand_knowledge_base(knowledge)
        except Exception as e:
            print(f"Warning: Could not load additional anatomical knowledge: {e}")
    
    def process_pdf(self, pdf_path):
        """Process PDF and extract injury data"""
        try:
            print(f"Processing PDF: {pdf_path}")
            # Extract injury data using the updated method
            injury_data = self.report_analyzer.analyze_injury_locations(pdf_path)
            
            if not injury_data:
                print("No injuries found in the PDF")
                injury_data = []
            
            # Save injury data for reference
            injury_json_path = self.output_dir / 'injury_data.json'
            with open(injury_json_path, 'w') as f:
                json.dump(injury_data, f, indent=4)
            
            print(f"Extracted injury data: {injury_data}")
            return injury_data
            
        except Exception as e:
            print(f"Error processing PDF: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def paint_model(self, injury_data, use_xray=None):
        """Paint the FBX model using Blender"""
        try:
            print("Starting 3D model processing - this may take up to 2 minutes...")
            
            # Check if Blender is installed and accessible
            try:
                # First check if Blender path is set in environment variables
                blender_path = os.environ.get('BLENDER_PATH', 'blender')  # Default to 'blender' if not set
                
                # If environment variable not set, try to find Blender in common installation paths
                if blender_path == 'blender':
                    common_paths = [
                        r'C:\Program Files\Blender Foundation\Blender 3.6',
                        r'C:\Program Files\Blender Foundation\Blender',
                        '/usr/bin/blender',
                        '/usr/local/bin/blender',
                        '/opt/blender/blender-2.93.13-linux-x64/blender',
                        '/Applications/Blender.app/Contents/MacOS/Blender'
                    ]
                    
                    for path in common_paths:
                        if os.path.exists(os.path.join(path, 'blender.exe' if os.name == 'nt' else 'blender')):
                            blender_path = os.path.join(path, 'blender.exe' if os.name == 'nt' else 'blender')
                            break
                        elif os.path.exists(path):
                            blender_path = path
                            break
                
                # Check if blender is available by running a simple command
                try:
                    subprocess.run([blender_path, '--version'], capture_output=True, check=True)
                    print(f"Blender found at: {blender_path}")
                except (subprocess.SubprocessError, FileNotFoundError):
                    print("Blender not found. Attempting to install...")
                    
                    # Detect the operating system and install Blender
                    if os.name == 'nt':  # Windows
                        print("Automatic Blender installation on Windows is not supported.")
                        print("Please install Blender manually from https://www.blender.org/download/")
                        raise Exception("Blender not installed on Windows")
                    else:  # Linux/macOS
                        # Check if we're on a Debian/Ubuntu system
                        if os.path.exists('/usr/bin/apt'):
                            print("Detected Debian/Ubuntu system. Installing Blender...")
                            subprocess.run(['sudo', 'apt', 'update'], check=True)
                            subprocess.run(['sudo', 'apt', 'install', '-y', 'blender'], check=True)
                            blender_path = '/usr/bin/blender'
                        # Check if we're on a RHEL/CentOS system
                        elif os.path.exists('/usr/bin/yum'):
                            print("Detected RHEL/CentOS system. Installing Blender...")
                            subprocess.run(['sudo', 'yum', 'install', '-y', 'epel-release'], check=True)
                            subprocess.run(['sudo', 'yum', 'install', '-y', 'blender'], check=True)
                            blender_path = '/usr/bin/blender'
                        # Check if we're on macOS with Homebrew
                        elif os.path.exists('/usr/local/bin/brew') or os.path.exists('/opt/homebrew/bin/brew'):
                            print("Detected macOS with Homebrew. Installing Blender...")
                            brew_path = '/usr/local/bin/brew' if os.path.exists('/usr/local/bin/brew') else '/opt/homebrew/bin/brew'
                            subprocess.run([brew_path, 'install', 'blender'], check=True)
                            blender_path = '/usr/local/bin/blender'
                        else:
                            raise Exception("Unsupported operating system for automatic Blender installation")
                        
                        # Verify installation
                        try:
                            subprocess.run([blender_path, '--version'], capture_output=True, check=True)
                            print(f"Blender successfully installed at: {blender_path}")
                        except (subprocess.SubprocessError, FileNotFoundError):
                            raise Exception("Blender installation failed")
                
                print(f"Using Blender path: {blender_path}")
            except Exception as e:
                print(f"Error finding or installing Blender: {e}")
                raise Exception(f"Blender not found or could not be installed: {str(e)}")

            # Generate unique output path for this visualization
            output_path = self.output_dir / f'painted_model_{int(time.time())}.glb'
            
            # Ensure output directory exists
            os.makedirs(self.output_dir, exist_ok=True)
            
            # Create a temporary directory for our script and module
            with tempfile.TemporaryDirectory() as temp_dir:
                # Copy all necessary modules to temp directory
                modules_to_copy = [
                    'paint_fbx_model.py',
                    'mistral_analysis_service.py',
                    '__init__.py'
                ]
                
                for module in modules_to_copy:
                    source_path = self.script_dir / module
                    if os.path.exists(source_path):
                        shutil.copy2(source_path, Path(temp_dir) / module)
                    else:
                        print(f"Warning: Module {module} not found at {source_path}")
                
                # Create empty __init__.py if it doesn't exist
                init_path = Path(temp_dir) / '__init__.py'
                if not os.path.exists(init_path):
                    open(init_path, 'w').close()
                
                # Create temporary Python script for Blender with enhanced export settings
                # Add careful error handling around the use_xray JSON serialization
                try:
                    # Set the use_xray parameter
                    # Convert use_xray to None, True or False explicitly before JSON serialization
                    # to avoid any Python-specific structures that might cause issues in the script
                    use_xray_value = None
                    if use_xray is True:
                        use_xray_value = True
                    elif use_xray is False:
                        use_xray_value = False
                    
                    use_xray_str = json.dumps(use_xray_value)
                    use_xray_script = f"use_xray = {use_xray_str}"
                    print(f"Setting use_xray in script to: {use_xray_str}")
                except Exception as e:
                    print(f"Error handling use_xray parameter: {e}")
                    use_xray_script = "use_xray = None"
                    print("Defaulting use_xray to None due to error")
                
                script_content = f"""
import bpy
import sys
import os
import math

# Set minimal preferences for compatibility with older Blender versions
# Avoid using advanced features that may not be available in all versions
try:
    bpy.context.preferences.view.show_developer_ui = False
except AttributeError:
    print("Could not set show_developer_ui preference - ignoring")

try:
    bpy.context.preferences.system.memory_cache_limit = 1024  # Limit memory usage
except AttributeError:
    print("Could not set memory_cache_limit preference - ignoring")

# Add the current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Add parent directory to Python path for imports
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

try:
    from paint_fbx_model import InjuryVisualizer
    
    # Load injury data
    injury_data = {json.dumps(injury_data)}
    
    # Initialize visualizer and process
    fbx_path = r"{str(self.fbx_path.resolve())}"
    output_path = r"{str(output_path.resolve())}"
    
    # Set the use_xray parameter with defensive handling
    try:
        {use_xray_script}
        print(f"Using X-ray: {{use_xray if use_xray is not None else 'Using config default'}}")
    except Exception as xray_error:
        print(f"Error setting use_xray parameter: {{str(xray_error)}}")
        print("Defaulting to None (use config setting)")
        use_xray = None
    
    print(f"Loading FBX from: {{fbx_path}}")
    print(f"Output will be saved to: {{output_path}}")
    
    # Use the most basic rendering settings that work across all Blender versions
    try:
        # This should work in Blender 2.8+
        bpy.context.scene.render.engine = 'BLENDER_WORKBENCH'
    except Exception:
        # Fallback for older versions
        print("Could not set render engine to BLENDER_WORKBENCH, using default")
    
    # Use only the most basic settings that should work in all Blender versions
    # Set up basic lighting with minimal settings
    # Remove all existing lights first
    for obj in bpy.data.objects:
        if obj.type == 'LIGHT':
            bpy.data.objects.remove(obj)
    
    # Create just one simple light
    key_light = bpy.data.lights.new(name="Key_Light", type='SUN')
    key_light.energy = 5.0
    key_light_obj = bpy.data.objects.new("Key_Light", key_light)
    bpy.context.collection.objects.link(key_light_obj)
    key_light_obj.rotation_euler = (math.radians(45), 0, math.radians(135))
    
    # Create visualizer and process injuries
    print("Creating injury visualizer...")
    visualizer = InjuryVisualizer(fbx_path)
    print("Processing injury data...")
    visualizer.process_injury_data(injury_data, use_xray)
    
    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    os.makedirs(output_dir, exist_ok=True)
    
    # Export with minimal settings
    print("Exporting to GLB...")
    try:
        bpy.ops.export_scene.gltf(
            filepath=output_path,
            export_format='GLB'
        )
    except Exception as export_error:
        print(f"Error with default export: {{str(export_error)}}")
        # Try minimal export params
        try:
            bpy.ops.export_scene.gltf(
                filepath=output_path
            )
        except Exception as minimal_error:
            print(f"Error with minimal export: {{str(minimal_error)}}")
            # Last resort - try to save as a Blender file
            print("Trying to save as .blend file instead...")
            blend_path = output_path.replace('.glb', '.blend')
            bpy.ops.wm.save_as_mainfile(filepath=blend_path)
            print(f"Saved .blend file to {{blend_path}}")
    
    # Verify file was created
    if os.path.exists(output_path):
        print(f"Successfully exported model to: {{output_path}}")
        print(f"File size: {{os.path.getsize(output_path)}} bytes")
    else:
        print(f"WARNING: Export appears to have failed, {{output_path}} not found")
        # Check if we saved a .blend file instead
        blend_path = output_path.replace('.glb', '.blend')
        if os.path.exists(blend_path):
            print(f"But .blend file was saved to {{blend_path}}")
            # Manually note that we need to convert the .blend file
            print("BLEND_FILE_CREATED=1")
    
except Exception as e:
    print(f"Error in Blender script: {{str(e)}}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
"""
                
                # Save script to temporary directory
                temp_script_path = Path(temp_dir) / 'run_blender.py'
                with open(temp_script_path, 'w') as f:
                    f.write(script_content)
                
                # Check if we're running in a cloud environment (Google Cloud Run)
                is_cloud_environment = os.environ.get('K_SERVICE') is not None or os.environ.get('CLOUD_RUN') == 'true'
                print(f"Detected cloud environment: {is_cloud_environment}")
                
                # Check if Xvfb is available for headless rendering
                has_xvfb = False
                has_xauth = False
                try:
                    subprocess.run(['which', 'xvfb-run'], capture_output=True, check=True)
                    has_xvfb = True
                    # Also check if xauth is available
                    try:
                        subprocess.run(['which', 'xauth'], capture_output=True, check=True)
                        has_xauth = True
                    except (subprocess.SubprocessError, FileNotFoundError):
                        print("xauth not found, cannot use xvfb-run")
                    print("Xvfb is available for headless rendering")
                except (subprocess.SubprocessError, FileNotFoundError):
                    print("Xvfb not found, will try direct Blender execution")
                
                try:
                    # Prepare the Blender command
                    blender_cmd = [
                        blender_path,
                        '--background',
                        '--factory-startup',  # Use factory settings to avoid loading user preferences
                        '--enable-autoexec',  # Enable auto execution of Python scripts
                        '--python-use-system-env',  # Use system Python environment
                        '-f', '0',  # Force execution, ensures headless mode is enforced
                        '--python', str(temp_script_path.resolve()),  # Use resolved absolute path
                        '-noaudio'  # Disable audio to prevent potential issues
                    ]
                    
                    # Use Xvfb if available and in cloud environment and xauth is available
                    if has_xvfb and is_cloud_environment and has_xauth:
                        print("Using Xvfb for headless rendering in cloud environment")
                        cmd = ['xvfb-run', '-a', '-s', '-screen 0 1280x720x24'] + blender_cmd
                        print(f"Running command with Xvfb: {' '.join(cmd)}")
                        
                        # Set environment variables for Blender in headless mode
                        env = os.environ.copy()
                        env['PYTHONPATH'] = f"{temp_dir}:{env.get('PYTHONPATH', '')}"
                        
                        # Add CPU compatibility environment variables to prevent "Illegal instruction" errors
                        env['OPENBLAS_CORETYPE'] = 'ARMV8'  # Helps with some numeric libraries
                        env['MESA_LOADER_DRIVER_OVERRIDE'] = 'i965'  # Force Intel graphics even in cloud
                        env['GALLIUM_DRIVER'] = 'llvmpipe'  # Use software rendering
                        
                        # Special handling for Google Cloud Run: don't set DISPLAY
                        if os.environ.get('K_SERVICE') is not None:
                            print("Detected Google Cloud Run - running Blender without setting DISPLAY")
                            # Remove DISPLAY if it exists
                            if 'DISPLAY' in env:
                                del env['DISPLAY']
                        else:
                            # For other cloud environments, set DISPLAY=:0
                            env['DISPLAY'] = ':0'
                        
                        result = subprocess.run(
                            cmd,
                            capture_output=True,
                            text=True,
                            env=env
                        )
                    else:
                        # Standard execution - in cloud environment without xauth, try direct execution
                        if is_cloud_environment:
                            print("Running in cloud environment without Xvfb (xauth not available). Using direct Blender execution.")
                            # When running in cloud environment without xvfb, set DISPLAY=:0
                            env = os.environ.copy()
                            env['PYTHONPATH'] = f"{temp_dir}:{env.get('PYTHONPATH', '')}"
                            
                            # Add CPU compatibility environment variables to prevent "Illegal instruction" errors
                            env['OPENBLAS_CORETYPE'] = 'ARMV8'  # Helps with some numeric libraries
                            env['MESA_LOADER_DRIVER_OVERRIDE'] = 'i965'  # Force Intel graphics even in cloud
                            env['GALLIUM_DRIVER'] = 'llvmpipe'  # Use software rendering
                            
                            # Special handling for Google Cloud Run: don't set DISPLAY
                            if os.environ.get('K_SERVICE') is not None:
                                print("Detected Google Cloud Run - running Blender without setting DISPLAY")
                                # Remove DISPLAY if it exists
                                if 'DISPLAY' in env:
                                    del env['DISPLAY']
                            else:
                                # For other cloud environments, set DISPLAY=:0
                                env['DISPLAY'] = ':0'
                            
                            # Run with custom environment
                            print(f"Running Blender command: {' '.join(blender_cmd)}")
                            result = subprocess.run(
                                blender_cmd,
                                capture_output=True,
                                text=True,
                                env=env
                            )
                        else:
                            # Standard execution for non-cloud
                            print(f"Running Blender command: {' '.join(blender_cmd)}")
                            result = subprocess.run(
                                blender_cmd,
                                capture_output=True,
                                text=True
                            )
                    
                    # Check if the command was successful
                    if result.returncode != 0:
                        print("Blender command failed with return code:", result.returncode)
                        print("Blender Output:")
                        print(result.stdout)
                        print("Blender Errors:")
                        print(result.stderr)
                        
                        raise Exception(f"Blender process failed with return code {result.returncode}")
                    
                    print("Blender Output:")
                    print(result.stdout)
                    
                    if result.stderr:
                        print("Blender Errors:")
                        print(result.stderr)
                
                    # Check for "BLEND_FILE_CREATED" in the output
                    # This indicates that the GLB export failed but a .blend file was created
                    blend_file_created = "BLEND_FILE_CREATED=1" in result.stdout
                    blend_path = str(output_path).replace('.glb', '.blend')
                    
                    # Verify the output file was created
                    if os.path.exists(output_path):
                        file_size = os.path.getsize(output_path)
                        print(f"Successfully painted and saved model to: {output_path} (size: {file_size} bytes)")
                        if file_size == 0:
                            raise Exception("Output file was created but is empty")
                        return str(output_path)
                    elif blend_file_created and os.path.exists(blend_path):
                        print(f"GLB export failed but .blend file was created at: {blend_path}")
                        # Try to convert the .blend file to GLB using a simpler approach
                        print("Attempting to convert .blend file to GLB...")
                        converted_output_path = self.output_dir / f'converted_model_{int(time.time())}.glb'
                        
                        # We'll use a simpler Blender command to just load and export the file
                        conversion_script = f"""
import bpy
import sys

try:
    # Load the blend file
    bpy.ops.wm.open_mainfile(filepath="{blend_path}")
    
    # Export to GLB with minimal settings
    bpy.ops.export_scene.gltf(filepath="{converted_output_path}", export_format='GLB')
    
    print(f"Successfully converted to GLB: {converted_output_path}")
except Exception as e:
    print(f"Error converting .blend to GLB: {str(e)}")
    sys.exit(1)
"""
                        # Save conversion script to a temporary file
                        with tempfile.NamedTemporaryFile(suffix='.py', mode='w', delete=False) as temp_file:
                            temp_script_path = temp_file.name
                            temp_file.write(conversion_script)
                        
                        try:
                            # Run Blender to convert the file
                            conversion_cmd = [
                                blender_path,
                                '--background',
                                '--factory-startup',
                                '--python', temp_script_path
                            ]
                            
                            print(f"Running conversion command: {' '.join(conversion_cmd)}")
                            conv_result = subprocess.run(
                                conversion_cmd,
                                capture_output=True,
                                text=True
                            )
                            
                            print("Conversion Output:")
                            print(conv_result.stdout)
                            
                            if conv_result.stderr:
                                print("Conversion Errors:")
                                print(conv_result.stderr)
                            
                            # Check if the conversion was successful
                            if os.path.exists(converted_output_path):
                                return str(converted_output_path)
                        except Exception as conv_error:
                            print(f"Error during conversion: {str(conv_error)}")
                        finally:
                            # Clean up temporary script
                            os.unlink(temp_script_path)
                    
                    raise Exception(f"Output file was not created at {output_path}")
                
                except subprocess.CalledProcessError as e:
                    print(f"Blender process error: {str(e)}")
                    # Print the captured stdout and stderr
                    print("Blender Output:")
                    print(e.stdout if hasattr(e, 'stdout') else "No stdout available")
                    print("Blender Errors:")
                    print(e.stderr if hasattr(e, 'stderr') else "No stderr available")
                    
                    # Check for specific error messages in the output
                    stdout_str = e.stdout if hasattr(e, 'stdout') and e.stdout else ""
                    stderr_str = e.stderr if hasattr(e, 'stderr') and e.stderr else ""
                    
                    if "NameError: name 'use_xray' is not defined" in stdout_str or "NameError: name 'use_xray' is not defined" in stderr_str:
                        print("Error with use_xray parameter - fixing the script...")
                        
                        # Create a simplified script that doesn't use the use_xray parameter
                        simplified_script = script_content.replace(
                            "visualizer.process_injury_data(injury_data, use_xray)",
                            "visualizer.process_injury_data(injury_data)"
                        )
                        
                        # Write the simplified script
                        with open(temp_script_path, 'w') as f:
                            f.write(simplified_script)
                        
                        print("Trying again with simplified script...")
                        
                        # Use Xvfb if available and in cloud environment
                        if has_xvfb and is_cloud_environment and has_xauth:
                            cmd = ['xvfb-run', '-a', '-s', '-screen 0 1280x720x24'] + blender_cmd
                            env = os.environ.copy()
                            env['PYTHONPATH'] = f"{temp_dir}:{env.get('PYTHONPATH', '')}"
                            env['DISPLAY'] = ':99'
                            retry_result = subprocess.run(cmd, capture_output=True, text=True, env=env)
                        elif is_cloud_environment:
                            # Cloud environment without xauth - try direct execution
                            env = os.environ.copy()
                            env['PYTHONPATH'] = f"{temp_dir}:{env.get('PYTHONPATH', '')}"
                            
                            # Add CPU compatibility environment variables to prevent "Illegal instruction" errors
                            env['OPENBLAS_CORETYPE'] = 'ARMV8'  # Helps with some numeric libraries
                            env['MESA_LOADER_DRIVER_OVERRIDE'] = 'i965'  # Force Intel graphics even in cloud
                            env['GALLIUM_DRIVER'] = 'llvmpipe'  # Use software rendering
                            
                            # Special handling for Google Cloud Run: don't set DISPLAY
                            if os.environ.get('K_SERVICE') is not None:
                                print("Detected Google Cloud Run - running Blender without setting DISPLAY")
                                # Remove DISPLAY if it exists
                                if 'DISPLAY' in env:
                                    del env['DISPLAY']
                            else:
                                # For other cloud environments, set DISPLAY=:0
                                env['DISPLAY'] = ':0'
                                
                            print("Retrying with direct Blender execution in cloud environment")
                            retry_result = subprocess.run(blender_cmd, capture_output=True, text=True, env=env)
                        else:
                            # Standard execution for non-cloud
                            retry_result = subprocess.run(blender_cmd, capture_output=True, text=True)
                        
                        if retry_result.returncode == 0:
                            print("Simplified script succeeded!")
                            # Verify the output file was created after retry
                            if os.path.exists(output_path):
                                file_size = os.path.getsize(output_path)
                                print(f"Successfully painted and saved model to: {output_path} (size: {file_size} bytes)")
                                if file_size == 0:
                                    raise Exception("Output file was created but is empty")
                                return str(output_path)
                        else:
                            print("Simplified script also failed:")
                            print(retry_result.stdout)
                            print(retry_result.stderr)
                    
                    # If all else fails, raise the exception
                    if is_cloud_environment:
                        print("Attempting cloud-specific fallback after error...")
                        
                        # Create a simplified GLB file without using Blender
                        fallback_output_path = self.output_dir / f'fallback_model_{int(time.time())}.glb'
                        
                        # Copy a pre-processed model if available
                        fallback_model_path = self.script_dir / 'fallback_models' / 'basic_human_model.glb'
                        if os.path.exists(fallback_model_path):
                            print(f"Using fallback model from: {fallback_model_path}")
                            shutil.copy2(fallback_model_path, fallback_output_path)
                            print(f"Fallback model copied to: {fallback_output_path}")
                            return str(fallback_output_path)
                    
                    raise Exception(f"Blender processing failed: {str(e)}")
                
        except Exception as e:
            print(f"Error painting model: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Check if the error is related to Blender not being found
            is_blender_missing = "No such file or directory: 'blender'" in str(e) or "FileNotFoundError" in str(e) or "command not found" in str(e)
            if is_blender_missing:
                print("Blender executable not found. Attempting to install Blender...")
                try:
                    # Try to install Blender using the installation script
                    install_script = os.path.join(self.script_dir, "install_blender.sh")
                    
                    if os.path.exists(install_script):
                        print(f"Found Blender installation script at {install_script}")
                        # Make the script executable
                        subprocess.run(["chmod", "+x", install_script], check=False)
                        # Run the installation script
                        install_result = subprocess.run([install_script], check=False, capture_output=True, text=True)
                        
                        print(f"Blender installation script output: {install_result.stdout}")
                        if install_result.returncode != 0:
                            print(f"Blender installation failed: {install_result.stderr}")
                    else:
                        print(f"Blender installation script not found at {install_script}")
                except Exception as install_error:
                    print(f"Error attempting to install Blender: {install_error}")
            
            # Check for docker or container environment for additional fallbacks
            is_container = os.path.exists("/.dockerenv") or os.environ.get("CONTAINER", "") == "true"
            is_cloud_environment = os.environ.get('K_SERVICE') is not None or os.environ.get('CLOUD_RUN') == 'true'
            
            if is_container or is_cloud_environment:
                print("Running in container/cloud environment, trying fallback models...")
                
                # Create fallback directory if it doesn't exist
                fallback_dir = self.script_dir / 'fallback_models'
                os.makedirs(fallback_dir, exist_ok=True)
                
                # Use a basic fallback model
                fallback_output_path = self.output_dir / f'emergency_fallback_model_{int(time.time())}.glb'
                
                # Check in multiple locations for fallback models
                possible_locations = [
                    self.script_dir / 'fallback_models',
                    self.script_dir / 'models',
                    self.script_dir / 'static' / 'models',
                    Path('/app/fallback_models'),
                    Path('/app/models')
                ]
                
                for location in possible_locations:
                    if location.exists():
                        print(f"Checking for fallback models in {location}")
                        fallback_files = list(location.glob('*.glb'))
                        if fallback_files:
                            print(f"Using emergency fallback model: {fallback_files[0]}")
                            shutil.copy2(fallback_files[0], fallback_output_path)
                            print(f"Emergency fallback model copied to: {fallback_output_path}")
                            return str(fallback_output_path)
                
                # If no model found, create a simple dummy model with a text message 
                print("No fallback models found, creating dummy model...")
                try:
                    # Create a JSON file indicating the error
                    error_info = self.output_dir / 'error_info.json'
                    with open(error_info, 'w') as f:
                        import json
                        json.dump({
                            "error": "Blender not available",
                            "message": "Failed to paint model due to missing Blender installation",
                            "timestamp": time.time(),
                            "original_error": str(e)
                        }, f)
                    
                    # Create a dummy model (just a text file with .glb extension)
                    dummy_model = self.output_dir / f'dummy_model_{int(time.time())}.glb'
                    with open(dummy_model, 'w') as f:
                        f.write("ERROR: Blender not available. Please install Blender.")
                    
                    print(f"Created dummy model at {dummy_model}")
                    return str(dummy_model)
                except Exception as dummy_error:
                    print(f"Failed to create dummy model: {dummy_error}")
            
            # If all fallbacks fail, raise the exception
            raise Exception(f"Failed to paint model: {str(e)}")
    
    def process_and_visualize(self, injury_data, use_xray=None):
        """Process injury data and generate 3D visualization"""
        try:
            print("Starting 3D injury visualization process - this may take up to 2 minutes...")
            print(f"Processing injury data: {injury_data}")
            print(f"X-ray visualization: {use_xray if use_xray is not None else 'Using default from config'}")
            
            # Handle empty or invalid injury data by providing a default
            if not injury_data:
                print("No injury data provided, using empty data set")
                injury_data = []
            elif not isinstance(injury_data, list):
                print("Invalid injury data format, converting to list")
                try:
                    if isinstance(injury_data, str):
                        # Try to parse as JSON if it's a string
                        import json
                        injury_data = json.loads(injury_data)
                    else:
                        # Otherwise, wrap it in a list
                        injury_data = [injury_data]
                except:
                    print("Could not convert injury data, using empty data set")
                    injury_data = []
            
            # Process injury data
            processed_injuries = self.process_injury_data(injury_data)
            print(f"Processed injuries: {processed_injuries}")
            
            try:
                # Paint the model with injuries (even if empty)
                painted_model_path = self.paint_model(processed_injuries, use_xray)
                return painted_model_path
            except Exception as blender_error:
                if "Blender not found" in str(blender_error) or "Blender installation failed" in str(blender_error):
                    print("Blender error detected. Providing detailed error message.")
                    error_message = (
                        "Blender is required for 3D model visualization but is not installed on the server. "
                        "Please install Blender using one of the following methods:\n\n"
                        "For Ubuntu/Debian: sudo apt update && sudo apt install -y blender xauth\n"
                        "For CentOS/RHEL: sudo yum install -y epel-release && sudo yum install -y blender xauth\n"
                        "For Docker: Add 'RUN apt-get update && apt-get install -y blender xauth' to your Dockerfile\n\n"
                        "After installation, restart the application."
                    )
                    raise Exception(error_message) from blender_error
                else:
                    # Pass through the original error
                    raise blender_error
            
        except Exception as e:
            print(f"Error in visualization process: {str(e)}")
            import traceback
            traceback.print_exc()
            # Pass through the original error without wrapping it
            raise e

    def create_visualizer(self, model_path=None):
        """Create and return an InjuryVisualizer instance with AI-enhanced mesh detection"""
        try:
            from paint_fbx_model import InjuryVisualizer
            
            # Use provided model path or default to base FBX
            target_path = model_path if model_path else str(self.fbx_path)
            print(f"Creating visualizer for model: {target_path}")
            
            # Create visualizer instance
            visualizer = InjuryVisualizer(target_path)
            
            # Pass AI service to visualizer if available
            if hasattr(self, 'ai_service') and self.ai_service:
                try:
                    visualizer.ai_service = self.ai_service
                    print("Passed AI service to visualizer for improved mesh detection")
                except Exception as e:
                    print(f"Warning: Could not pass AI service to visualizer: {e}")
            
            return visualizer
            
        except Exception as e:
            print(f"Error creating visualizer: {str(e)}")
            traceback.print_exc()
            raise

    def process_injury_data(self, extracted_injuries):
        """
        Process extracted injury data into a structured format for visualization
        with AI-enhanced body part recognition
        """
        processed_injuries = []
        
        for injury in extracted_injuries:
            try:
                body_part = injury.get('bodyPart', '').lower()
                side = injury.get('side', '').lower()
                injury_type = injury.get('injuryType', '').lower()
                severity = injury.get('severity', '').lower()
                status = injury.get('status', '').lower()
                
                # Skip if missing required data
                if not body_part:
                    print("Skipping injury with missing body part")
                    continue
                
                # Use AI service to improve body part recognition if available
                if hasattr(self, 'ai_service') and self.ai_service:
                    try:
                        # Get all known body parts from our mapping
                        known_body_parts = list(self.body_part_mapping.keys()) + list(set(self.body_part_mapping.values()))
                        
                        # Find the best match for this body part
                        matches = self.ai_service.find_matching_meshes(body_part, known_body_parts)
                        if matches:
                            best_match = matches[0]
                            print(f"AI improved body part recognition: '{body_part}' -> '{best_match}'")
                            
                            # Use the best match if it's in our mapping
                            if best_match in self.body_part_mapping:
                                body_part = self.body_part_mapping[best_match]
                            else:
                                body_part = best_match
                    except Exception as e:
                        print(f"Warning: AI body part recognition failed: {e}")
                
                # Map body part to standardized name if available
                if body_part in self.body_part_mapping:
                    standardized_body_part = self.body_part_mapping[body_part]
                    print(f"Mapped body part '{body_part}' to standardized name '{standardized_body_part}'")
                    body_part = standardized_body_part
                
                processed_injury = {
                    'bodyPart': body_part,
                    'side': side,
                    'injuryType': injury_type,
                    'severity': severity,
                    'status': status
                }
                
                processed_injuries.append(processed_injury)
            except Exception as e:
                print(f"Error processing individual injury {injury}: {e}")
                # Continue with next injury
        
        print(f"Processed {len(processed_injuries)} injuries")
        return processed_injuries

    def process_and_visualize_from_pdf(self, pdf_path, use_xray=None):
        """Main function to process PDF and visualize injuries"""
        try:
            print("Starting PDF processing and 3D visualization - this may take up to 2 minutes...")
            print(f"Processing PDF: {pdf_path}")
            print(f"X-ray visualization: {use_xray if use_xray is not None else 'Using default from config'}")
            
            # Step 1: Process PDF and extract injury data
            injury_data = self.process_pdf(pdf_path)
            if not injury_data:
                print("No injury data found, creating empty visualization")
                injury_data = []
            
            print(f"Successfully extracted {len(injury_data)} injuries")
            
            # Step 2: Try the enhanced visualization approach first (combines X-ray + Painting)
            try:
                from injury_xray_visualizer import InjuryXRayVisualizer
                print("Using enhanced visualization technique that combines X-ray transparency with injury coloring...")
                
                # Create X-ray visualizer with our model paths
                visualizer = InjuryXRayVisualizer(str(self.fbx_path), str(self.output_dir))
                
                # Generate optimal visualizations (now prioritizes the enhanced version)
                visualization_results = visualizer.generate_optimal_visualizations(injury_data)
                
                # First try to use the enhanced version which combines X-ray + painting
                if 'enhanced' in visualization_results:
                    result_path = visualization_results['enhanced']
                    print(f"Successfully created enhanced visualization (X-ray + painting) at: {result_path}")
                    return {
                        'status': 'success',
                        'injury_data': injury_data,
                        'model_path': result_path
                    }
                
                # Fall back to X-ray if enhanced fails
                elif 'xray' in visualization_results:
                    result_path = visualization_results['xray']
                    print(f"Using X-ray visualization as fallback at: {result_path}")
                    return {
                        'status': 'success',
                        'injury_data': injury_data,
                        'model_path': result_path
                    }
                
                # Fall back to cutaway if X-ray fails
                elif 'cutaway' in visualization_results:
                    result_path = visualization_results['cutaway']
                    print(f"Using cutaway visualization as fallback at: {result_path}")
                    return {
                        'status': 'success',
                        'injury_data': injury_data,
                        'model_path': result_path
                    }
                
                else:
                    print("Enhanced visualization failed, falling back to standard method")
            except Exception as e:
                print(f"Error with enhanced visualization: {str(e)}")
                print("Falling back to standard visualization method")
            
            # Step 3: Fall back to standard visualization if enhanced approach fails
            try:
                painted_model_path = self.process_and_visualize(injury_data, use_xray)
                
                if not painted_model_path:
                    raise Exception("Failed to create visualization")
                    
                print(f"Successfully created standard visualization at: {painted_model_path}")
                
                return {
                    'status': 'success',
                    'injury_data': injury_data,
                    'model_path': painted_model_path
                }
            except Exception as blender_error:
                # Handle Blender-related errors more intelligently
                error_message = str(blender_error)
                
                # Common Blender error signatures
                blender_error_signatures = [
                    "Blender is required", 
                    "Blender not found", 
                    "Blender installation failed",
                    "xauth not found", 
                    "xvfb-run: error", 
                    "Command '['blender"
                ]
                
                if any(sig in error_message for sig in blender_error_signatures):
                    print(f"Blender-related error: {error_message}")
                    
                    # Detailed message for specific error types
                    if "xauth not found" in error_message or "xvfb-run: error: xauth command not found" in error_message:
                        detail_message = (
                            "The xauth command is missing. Please install it using:\n"
                            "For Ubuntu/Debian: sudo apt-get install -y xauth\n"
                            "For Docker: Add 'xauth' to the apt-get install line in your Dockerfile"
                        )
                    else:
                        detail_message = error_message
                    
                    return {
                        'status': 'error',
                        'message': detail_message,
                        'error_type': 'blender_execution_error',
                        'injury_data': injury_data  # Still return the processed injury data
                    }
                else:
                    # For other unexpected errors, pass through
                    print(f"Unexpected error during visualization: {error_message}")
                    return {
                        'status': 'error',
                        'message': f"Error during model visualization: {error_message}",
                        'error_type': 'visualization_error',
                        'injury_data': injury_data
                    }
            
        except Exception as e:
            print(f"Error in visualization process: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'status': 'error',
                'message': str(e)
            }

# Example usage
if __name__ == "__main__":
    service = InjuryVisualizationService()
    
    # # Sample injury data for testing - COMMENTED OUT
    # sample_injuries = [
    #     {
    #         "bodyPart": "biceps",
    #         "side": "right", 
    #         "injuryType": "strain",
    #         "severity": "moderate",
    #         "status": "active"
    #     },
    #     {
    #         "bodyPart": "quadriceps",
    #         "side": "left", 
    #         "injuryType": "bruise",
    #         "severity": "mild",
    #         "status": "past"
    #     }
    # ]
    # 
    # # Use sample data for testing
    # print("Testing with sample injury data...")
    # result = service.process_and_visualize(sample_injuries)
    # print(f"Result: {result}")
    
    # Use PDF file for injury data extraction
    pdf_path = "D:/flutter_temp/tmpbin8871b.pdf"  # Path from the logs
    print(f"Processing PDF file: {pdf_path}")
    result = service.process_and_visualize_from_pdf(pdf_path)
    print(f"Result: {result}") 