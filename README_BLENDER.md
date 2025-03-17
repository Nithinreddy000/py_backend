# Blender Installation Guide

This guide provides instructions for installing Blender, which is required for the 3D injury visualization functionality.

## Automatic Installation

You can use the provided installation script to automatically install Blender:

```bash
# Make the script executable
chmod +x install_blender.sh

# Run the script
./install_blender.sh
```

## Manual Installation

### Ubuntu/Debian

```bash
sudo apt update
sudo apt install -y blender
```

### CentOS/RHEL

```bash
sudo yum install -y epel-release
sudo yum install -y blender
```

### macOS

Using Homebrew:

```bash
brew install blender
```

### Windows

1. Download the installer from the [official Blender website](https://www.blender.org/download/)
2. Run the installer and follow the instructions
3. Add Blender to your system PATH

## Docker Installation

If you're using Docker, you can include Blender in your Dockerfile:

```dockerfile
FROM python:3.9

# Install Blender
RUN apt-get update && apt-get install -y \
    blender \
    && rm -rf /var/lib/apt/lists/*

# Rest of your Dockerfile...
```

## Verifying Installation

To verify that Blender is installed correctly, run:

```bash
blender --version
```

This should output the Blender version information.

## Troubleshooting

If you encounter the error `FileNotFoundError: [Errno 2] No such file or directory: 'blender'`, it means that Blender is not installed or not in your system PATH.

### Common Issues

1. **Blender not in PATH**: Add the Blender installation directory to your system PATH
2. **Permission issues**: Make sure you have the necessary permissions to run Blender
3. **Missing dependencies**: Install any missing dependencies required by Blender

For more help, please refer to the [official Blender documentation](https://docs.blender.org/manual/en/latest/getting_started/installing/index.html). 