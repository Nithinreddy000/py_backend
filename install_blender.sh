#!/bin/bash

# Script to install Blender on the server
# This script detects the operating system and installs Blender accordingly

echo "Blender Installation Script"
echo "==========================="

# Function to detect the operating system
detect_os() {
    if [ -f /etc/os-release ]; then
        # freedesktop.org and systemd
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
    elif type lsb_release >/dev/null 2>&1; then
        # linuxbase.org
        OS=$(lsb_release -si)
        VER=$(lsb_release -sr)
    elif [ -f /etc/lsb-release ]; then
        # For some versions of Debian/Ubuntu without lsb_release command
        . /etc/lsb-release
        OS=$DISTRIB_ID
        VER=$DISTRIB_RELEASE
    elif [ -f /etc/debian_version ]; then
        # Older Debian/Ubuntu/etc.
        OS=Debian
        VER=$(cat /etc/debian_version)
    else
        # Fall back to uname, e.g. "Linux <version>", also works for BSD, etc.
        OS=$(uname -s)
        VER=$(uname -r)
    fi
    
    echo "Detected OS: $OS $VER"
}

# Install Blender based on the detected OS
install_blender() {
    case "$OS" in
        *Ubuntu*|*Debian*)
            echo "Installing Blender on Ubuntu/Debian..."
            sudo apt-get update
            sudo apt-get install -y blender
            ;;
        *CentOS*|*Red\ Hat*|*RHEL*|*Fedora*)
            echo "Installing Blender on CentOS/RHEL/Fedora..."
            sudo yum install -y epel-release
            sudo yum install -y blender
            ;;
        *SUSE*)
            echo "Installing Blender on SUSE..."
            sudo zypper install -y blender
            ;;
        *Alpine*)
            echo "Installing Blender on Alpine Linux..."
            sudo apk add --no-cache blender
            ;;
        *)
            echo "Unsupported operating system: $OS"
            echo "Please install Blender manually."
            exit 1
            ;;
    esac
}

# Verify Blender installation
verify_installation() {
    echo "Verifying Blender installation..."
    if command -v blender >/dev/null 2>&1; then
        BLENDER_VERSION=$(blender --version | head -n 1)
        echo "Blender installed successfully: $BLENDER_VERSION"
        echo "Blender path: $(which blender)"
        return 0
    else
        echo "Blender installation failed or not in PATH."
        return 1
    fi
}

# Main execution
detect_os
install_blender
verify_installation

if [ $? -eq 0 ]; then
    echo "Installation completed successfully."
else
    echo "Installation failed. Please install Blender manually."
    exit 1
fi

echo "Done." 