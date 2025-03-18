#!/bin/bash
#
# Environment Checker Script
# This script checks if all necessary dependencies and configurations are in place
#

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ANSI colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print header
print_header() {
    echo -e "\n${BLUE}====== $1 ======${NC}"
}

# Print success message
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Print warning message
print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Print error message
print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Docker
check_docker() {
    print_header "Checking Docker"

    if command_exists docker; then
        DOCKER_VERSION=$(docker --version)
        print_success "Docker installed: $DOCKER_VERSION"
        
        # Check if Docker daemon is running
        if docker info >/dev/null 2>&1; then
            print_success "Docker daemon is running"
        else
            print_error "Docker daemon is not running"
            echo "  Start Docker with: 'sudo systemctl start docker' or run Docker Desktop"
            return 1
        fi
        
        # Check Docker Compose
        if command_exists docker-compose; then
            COMPOSE_VERSION=$(docker-compose --version)
            print_success "Docker Compose installed: $COMPOSE_VERSION"
        elif command_exists "docker compose"; then
            COMPOSE_VERSION=$(docker compose version)
            print_success "Docker Compose plugin installed: $COMPOSE_VERSION"
        else
            print_error "Docker Compose not found"
            echo "  Install Docker Compose with: 'sudo apt-get install docker-compose'"
            echo "  Or use Docker Desktop which includes Docker Compose"
            return 1
        fi
    else
        print_error "Docker not found"
        echo "  Install Docker with: 'sudo apt-get install docker.io' or download Docker Desktop"
        return 1
    fi
    
    return 0
}

# Check Python Environment
check_python() {
    print_header "Checking Python Environment"
    
    if command_exists python3; then
        PYTHON_VERSION=$(python3 --version)
        print_success "Python installed: $PYTHON_VERSION"
        
        # Check pip
        if command_exists pip3; then
            PIP_VERSION=$(pip3 --version)
            print_success "pip installed: $PIP_VERSION"
        else
            print_error "pip not found"
            echo "  Install pip with: 'sudo apt-get install python3-pip'"
            return 1
        fi
        
        # Check virtualenv
        if command_exists virtualenv; then
            VENV_VERSION=$(virtualenv --version)
            print_success "virtualenv installed: $VENV_VERSION"
        else
            print_warning "virtualenv not found (optional but recommended)"
            echo "  Install virtualenv with: 'pip3 install virtualenv'"
        fi
        
        # Check Python version is 3.8 or higher
        PY_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
        PY_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")
        
        if [[ "$PY_MAJOR" -ge 3 ]] && [[ "$PY_MINOR" -ge 8 ]]; then
            print_success "Python version is 3.8 or higher ($PY_MAJOR.$PY_MINOR)"
        else
            print_error "Python version $PY_MAJOR.$PY_MINOR is less than 3.8"
            echo "  Upgrade Python or use a Python version manager like pyenv"
            return 1
        fi
    else
        print_error "Python 3 not found"
        echo "  Install Python with: 'sudo apt-get install python3'"
        return 1
    fi
    
    return 0
}

# Check Blender
check_blender() {
    print_header "Checking Blender"
    
    if command_exists blender; then
        BLENDER_VERSION=$(blender --version | head -n 1)
        print_success "Blender installed: $BLENDER_VERSION"
    else
        print_warning "Blender not found in PATH"
        echo "  Note: Blender will be installed via Docker for production deployments"
        echo "  For local development, install Blender with: './install_blender.sh'"
    fi
    
    return 0
}

# Check Nginx (for production deployment)
check_nginx() {
    print_header "Checking Nginx"
    
    if command_exists nginx; then
        NGINX_VERSION=$(nginx -v 2>&1)
        print_success "Nginx installed: $NGINX_VERSION"
        
        # Check if Nginx config directory exists
        if [[ -d "nginx" ]]; then
            print_success "Nginx configuration directory exists"
            
            # Check if SSL directory exists
            if [[ -d "nginx/ssl" ]]; then
                print_success "SSL directory exists"
                
                # Check for SSL certificates
                if [[ -f "nginx/ssl/nginx.crt" ]] && [[ -f "nginx/ssl/nginx.key" ]]; then
                    print_success "SSL certificates found"
                else
                    print_warning "SSL certificates not found"
                    echo "  Generate self-signed certificates with: './nginx/generate_ssl.sh'"
                fi
            else
                print_warning "SSL directory not found"
                echo "  Create it with: 'mkdir -p nginx/ssl'"
            fi
        else
            print_warning "Nginx configuration directory not found"
            echo "  Creating nginx directory..."
            mkdir -p nginx/ssl nginx/conf.d
            print_success "Created nginx directories"
        fi
    else
        print_warning "Nginx not found (optional for local development)"
        echo "  Note: Nginx will be available via Docker for production deployments"
    fi
    
    return 0
}

# Check for required files and directories
check_files() {
    print_header "Checking Required Files and Directories"
    
    # Check for Dockerfile
    if [[ -f "Dockerfile" ]]; then
        print_success "Dockerfile exists"
    else
        print_error "Dockerfile not found"
        echo "  Create a Dockerfile for building the application"
        return 1
    fi
    
    # Check for docker-compose.yml
    if [[ -f "docker-compose.yml" ]]; then
        print_success "docker-compose.yml exists"
    else
        print_error "docker-compose.yml not found"
        echo "  Create a docker-compose.yml file for running the services"
        return 1
    fi
    
    # Check for app.py
    if [[ -f "app.py" ]]; then
        print_success "app.py exists"
    else
        print_error "app.py not found"
        echo "  Create the main application file app.py"
        return 1
    fi
    
    # Check for requirements.txt
    if [[ -f "requirements.txt" ]]; then
        print_success "requirements.txt exists"
    else
        print_error "requirements.txt not found"
        echo "  Create a requirements.txt file listing all dependencies"
        return 1
    fi
    
    # Check for model directories
    if [[ ! -d "models" ]]; then
        print_warning "models directory not found"
        echo "  Creating models directory..."
        mkdir -p models
        print_success "Created models directory"
    else
        print_success "models directory exists"
    fi
    
    # Check for data directory
    if [[ ! -d "data" ]]; then
        print_warning "data directory not found"
        echo "  Creating data directory..."
        mkdir -p data
        print_success "Created data directory"
    else
        print_success "data directory exists"
    fi
    
    # Check for logs directory
    if [[ ! -d "logs" ]]; then
        print_warning "logs directory not found"
        echo "  Creating logs directory..."
        mkdir -p logs
        print_success "Created logs directory"
    else
        print_success "logs directory exists"
    fi
    
    # Check for blender_files directory
    if [[ ! -d "blender_files" ]]; then
        print_warning "blender_files directory not found"
        echo "  Creating blender_files directory..."
        mkdir -p blender_files
        print_success "Created blender_files directory"
    else
        print_success "blender_files directory exists"
    fi
    
    return 0
}

# Check Python dependencies
check_python_dependencies() {
    print_header "Checking Python Dependencies"
    
    if [[ ! -f "requirements.txt" ]]; then
        print_error "requirements.txt not found"
        return 1
    fi
    
    echo "Checking for key dependencies in requirements.txt..."
    
    # List of critical dependencies
    DEPENDENCIES=(
        "flask"
        "torch"
        "torchvision"
        "ultralytics"
        "easyocr"
        "gunicorn"
        "cloudinary"
        "numpy"
        "opencv-python"
        "sentry-sdk"
        "blinker"
    )
    
    MISSING=0
    for dep in "${DEPENDENCIES[@]}"; do
        if grep -q -E "^$dep(==|>=|~=|$)" requirements.txt; then
            print_success "Found $dep in requirements.txt"
        else
            print_error "Missing $dep in requirements.txt"
            MISSING=1
        fi
    done
    
    if [[ $MISSING -eq 1 ]]; then
        print_warning "Some dependencies are missing in requirements.txt"
        echo "  Please update requirements.txt with the missing dependencies"
    else
        print_success "All critical dependencies are present in requirements.txt"
    fi
    
    return 0
}

# Verify download_models.py exists and is executable
check_download_script() {
    print_header "Checking Model Download Scripts"
    
    if [[ -f "download_models.py" ]]; then
        print_success "download_models.py exists"
        
        # Make executable if it's not
        if [[ ! -x "download_models.py" ]]; then
            chmod +x download_models.py
            print_success "Made download_models.py executable"
        else
            print_success "download_models.py is executable"
        fi
        
        # Check verify_models.py
        if [[ -f "verify_models.py" ]]; then
            print_success "verify_models.py exists"
            
            # Make executable if it's not
            if [[ ! -x "verify_models.py" ]]; then
                chmod +x verify_models.py
                print_success "Made verify_models.py executable"
            else
                print_success "verify_models.py is executable"
            fi
        else
            print_warning "verify_models.py not found"
            echo "  This script is recommended to verify model integrity"
        fi
    else
        print_warning "download_models.py not found"
        echo "  This script is recommended for downloading ML models"
    fi
    
    return 0
}

# Main function
main() {
    print_header "Environment Checker"
    echo "This script checks if your environment is ready for deployment"
    
    ERRORS=0
    
    # Run all checks
    check_docker || ((ERRORS++))
    check_python || ((ERRORS++))
    check_blender
    check_nginx
    check_files || ((ERRORS++))
    check_python_dependencies
    check_download_script
    
    # Summary
    print_header "Summary"
    if [[ $ERRORS -eq 0 ]]; then
        print_success "All essential checks passed. Your environment appears to be ready."
        echo "You can now proceed with deployment:"
        echo "  1. Run './download_models.py' to download ML models"
        echo "  2. Run 'docker-compose build' to build the Docker image"
        echo "  3. Run 'docker-compose up -d' to start the application"
    else
        print_error "$ERRORS essential checks failed. Please fix the issues before deployment."
    fi
}

# Run the main function
main 