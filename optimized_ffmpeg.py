#!/usr/bin/env python3

"""
This module provides optimized FFmpeg settings for faster video processing.
"""

import os
import subprocess
import platform
import shutil
from pathlib import Path

# Default encoding preset
DEFAULT_PRESET = "ultrafast"

def get_ffmpeg_path():
    """Get the path to the FFmpeg executable."""
    # First check the PATH
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        return ffmpeg_path
    
    # Otherwise use system-specific defaults
    if platform.system() == "Windows":
        return "C:\\ffmpeg\\bin\\ffmpeg.exe"
    else:
        return "/usr/bin/ffmpeg"

def get_gpu_encoding_settings():
    """Detect available GPU acceleration and return appropriate FFmpeg parameters."""
    # Try to detect GPU acceleration options
    print("Checking for GPU acceleration options...")
    
    try:
        # Check if ffmpeg supports h264_nvenc
        ffmpeg_help = subprocess.run(
            [get_ffmpeg_path(), "-encoders"], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True,
            timeout=5
        )
        
        # Check for NVIDIA GPU encoder
        if "h264_nvenc" in ffmpeg_help.stdout:
            print("Found NVIDIA GPU encoder (h264_nvenc)")
            return ["-c:v", "h264_nvenc", "-preset", "p1", "-tune", "ll"]
        
        # Check for Intel QuickSync encoder
        if "h264_qsv" in ffmpeg_help.stdout:
            print("Found Intel QuickSync encoder (h264_qsv)")
            return ["-c:v", "h264_qsv", "-preset", "veryfast"]
        
        # Check for VA-API encoder
        if "h264_vaapi" in ffmpeg_help.stdout:
            print("Found VA-API encoder (h264_vaapi)")
            return ["-c:v", "h264_vaapi", "-preset", "faster"]
        
    except Exception as e:
        print(f"Error checking GPU acceleration: {e}")
    
    # Fall back to CPU optimized settings
    print("Using CPU-optimized encoding (libx264)")
    return ["-c:v", "libx264", "-preset", DEFAULT_PRESET, "-tune", "zerolatency"]

def get_optimized_encoding_command(input_file, output_file, width=1280, height=720, 
                                   framerate=None, fast_start=True):
    """
    Get optimized FFmpeg command for fast video encoding.
    
    Args:
        input_file: Input video file path
        output_file: Output video file path
        width: Output width (default 1280)
        height: Output height (default 720)
        framerate: Output frame rate (if None, use source framerate)
        fast_start: Add faststart option for web streaming
        
    Returns:
        List of FFmpeg command arguments
    """
    ffmpeg = get_ffmpeg_path()
    encoding = get_gpu_encoding_settings()
    
    cmd = [ffmpeg, "-y", "-i", input_file]
    
    # Add framerate option if specified
    if framerate:
        cmd.extend(["-r", str(framerate)])
    
    # Scale the video
    cmd.extend(["-vf", f"scale={width}:{height}"])
    
    # Add encoding settings
    cmd.extend(encoding)
    
    # Add fast start for web streaming
    if fast_start:
        cmd.extend(["-movflags", "+faststart"])
    
    # Add audio settings (AAC is fast and efficient)
    cmd.extend(["-c:a", "aac", "-b:a", "128k"])
    
    # Add output file
    cmd.append(output_file)
    
    return cmd

def optimize_video(input_file, output_file, width=1280, height=720, framerate=None, fast_start=True):
    """
    Optimize a video file using FFmpeg with the best available hardware acceleration.
    
    Args:
        input_file: Input video file path
        output_file: Output video file path
        width: Output width (default 1280)
        height: Output height (default 720)
        framerate: Output frame rate (if None, use source framerate)
        fast_start: Add faststart option for web streaming
        
    Returns:
        Tuple of (success, error_message)
    """
    try:
        cmd = get_optimized_encoding_command(input_file, output_file, width, height, framerate, fast_start)
        print(f"Running FFmpeg command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            return False, f"FFmpeg error: {result.stderr}"
        
        return True, ""
    except Exception as e:
        return False, f"Error optimizing video: {str(e)}"

if __name__ == "__main__":
    # Test the module
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python optimized_ffmpeg.py input_file output_file")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    success, error = optimize_video(input_file, output_file)
    
    if success:
        print(f"Successfully optimized video: {output_file}")
    else:
        print(f"Failed to optimize video: {error}")
        sys.exit(1) 