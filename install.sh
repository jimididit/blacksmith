#!/bin/bash

# Blacksmith Installation Script
# This script installs Blacksmith from a GitHub repository

# Note: We use 'set -e' carefully - some commands may fail intentionally
# and we handle them with || or explicit error checking
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
REPO_URL="${BLACKSMITH_REPO:-https://github.com/jimididit/blacksmith.git}"
INSTALL_METHOD="${BLACKSMITH_INSTALL_METHOD:-venv}"  # venv (default), global, or user
BRANCH="${BLACKSMITH_BRANCH:-main}"

echo -e "${BLUE}🔨 Blacksmith Installation Script${NC}"
echo ""

# Check for Python
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
fi

if [ -z "$PYTHON_CMD" ]; then
    echo -e "${RED}✗ Python is not installed.${NC}"
    echo ""
    echo "Installation options:"
    echo "  Linux (Ubuntu/Debian): sudo apt install python3 python3-pip"
    echo "  Linux (Fedora/RHEL):   sudo dnf install python3 python3-pip"
    echo "  Linux (Arch):          sudo pacman -S python python-pip"
    echo "  Mac:                   brew install python3"
    echo "  Windows:               winget install Python.Python.3.12"
    echo "                         or download from https://www.python.org/downloads/"
    echo ""
    read -p "Would you like to attempt automatic installation? (y/N): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}Attempting to install Python...${NC}"
        
        # Try to detect package manager and install
        if command -v apt &> /dev/null; then
            echo "Detected apt. Installing Python..."
            sudo apt update && sudo apt install -y python3 python3-pip
            PYTHON_CMD="python3"
        elif command -v dnf &> /dev/null; then
            echo "Detected dnf. Installing Python..."
            sudo dnf install -y python3 python3-pip
            PYTHON_CMD="python3"
        elif command -v yum &> /dev/null; then
            echo "Detected yum. Installing Python..."
            sudo yum install -y python3 python3-pip
            PYTHON_CMD="python3"
        elif command -v pacman &> /dev/null; then
            echo "Detected pacman. Installing Python..."
            sudo pacman -S --noconfirm python python-pip
            PYTHON_CMD="python3"
        elif command -v brew &> /dev/null; then
            echo "Detected Homebrew. Installing Python..."
            brew install python3
            PYTHON_CMD="python3"
        elif command -v winget &> /dev/null; then
            echo "Detected winget. Installing Python..."
            winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements
            # Refresh PATH
            export PATH="$PATH:/c/Users/$USER/AppData/Local/Programs/Python/Python*/Scripts"
            PYTHON_CMD="python"
        elif command -v choco &> /dev/null; then
            echo "Detected Chocolatey. Installing Python..."
            choco install python3 -y
            PYTHON_CMD="python"
        else
            echo -e "${RED}✗ Could not detect a supported package manager.${NC}"
            echo "Please install Python manually using one of the methods above."
            exit 1
        fi
        
        # Verify installation
        if ! command -v $PYTHON_CMD &> /dev/null; then
            echo -e "${RED}✗ Python installation failed or not found in PATH.${NC}"
            echo "Please install Python manually and run this script again."
            exit 1
        fi
        
        echo -e "${GREEN}✓ Python installed successfully${NC}"
    else
        echo "Please install Python manually and run this script again."
        exit 1
    fi
fi

echo -e "${GREEN}✓${NC} Found Python: $(${PYTHON_CMD} --version)"

# Check Python version
PYTHON_VERSION=$(${PYTHON_CMD} -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.8"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo -e "${RED}✗ Python 3.8 or higher is required. Found: ${PYTHON_VERSION}${NC}"
    exit 1
fi

# Check for pip (use python -m pip to avoid launcher issues)
echo -e "${BLUE}Checking pip...${NC}"
if ${PYTHON_CMD} -m pip --version &> /dev/null; then
    PIP_VERSION=$(${PYTHON_CMD} -m pip --version 2>&1)
    echo -e "${GREEN}✓${NC} Found pip: ${PIP_VERSION}"
else
    echo -e "${YELLOW}⚠${NC} pip not found. Attempting to install..."
    ${PYTHON_CMD} -m ensurepip --upgrade || {
        echo -e "${RED}✗ Could not install pip. Please install pip manually.${NC}"
        exit 1
    }
    PIP_VERSION=$(${PYTHON_CMD} -m pip --version 2>&1)
    echo -e "${GREEN}✓${NC} Found pip: ${PIP_VERSION}"
fi

# Create temporary directory
TEMP_DIR=$(mktemp -d)
trap "rm -rf ${TEMP_DIR}" EXIT

echo ""
echo -e "${BLUE}Downloading Blacksmith...${NC}"

# Clone or download the repository
GIT_SUCCESS=false
if command -v git &> /dev/null; then
    echo "Cloning repository from ${REPO_URL}..."
    # Suppress git progress output (it goes to stderr and can confuse error handling)
    if git clone --depth 1 --branch "${BRANCH}" --quiet "${REPO_URL}" "${TEMP_DIR}/blacksmith" 2>&1; then
        GIT_SUCCESS=true
    else
        echo -e "${YELLOW}⚠${NC} Git clone failed, trying direct download..."
    fi
fi

# Fallback to direct download if git failed or not available
if [ "$GIT_SUCCESS" = false ]; then
    echo -e "${BLUE}Downloading repository as ZIP...${NC}"
    # Check for required tools for direct download
    if [[ "$REPO_URL" == *"github.com"* ]]; then
        # Check for curl or wget
        HAS_CURL=false
        HAS_WGET=false
        if command -v curl &> /dev/null; then
            HAS_CURL=true
        elif command -v wget &> /dev/null; then
            HAS_WGET=true
        else
            echo -e "${RED}✗ Neither curl nor wget found. Please install one of them or install git.${NC}"
            exit 1
        fi
        
        # Check for unzip
        if ! command -v unzip &> /dev/null; then
            echo -e "${RED}✗ unzip not found. Please install unzip or install git.${NC}"
            exit 1
        fi
        
        REPO_NAME=$(echo "$REPO_URL" | sed 's/.*github.com\///' | sed 's/\.git$//')
        DOWNLOAD_URL="https://github.com/${REPO_NAME}/archive/refs/heads/${BRANCH}.zip"
        
        if [ "$HAS_CURL" = true ]; then
            curl -L "${DOWNLOAD_URL}" -o "${TEMP_DIR}/blacksmith.zip" || {
                echo -e "${RED}✗ Failed to download Blacksmith${NC}"
                exit 1
            }
        else
            wget -O "${TEMP_DIR}/blacksmith.zip" "${DOWNLOAD_URL}" || {
                echo -e "${RED}✗ Failed to download Blacksmith${NC}"
                exit 1
            }
        fi
        
        unzip -q "${TEMP_DIR}/blacksmith.zip" -d "${TEMP_DIR}" || {
            echo -e "${RED}✗ Failed to extract Blacksmith${NC}"
            exit 1
        }
        mv "${TEMP_DIR}/blacksmith-${BRANCH}" "${TEMP_DIR}/blacksmith" || {
            echo -e "${RED}✗ Failed to prepare installation directory${NC}"
            exit 1
        }
    else
        echo -e "${RED}✗ Git is required for non-GitHub repositories. Please install git.${NC}"
        exit 1
    fi
fi

INSTALL_DIR="${TEMP_DIR}/blacksmith"

if [ ! -d "${INSTALL_DIR}" ]; then
    echo -e "${RED}✗ Installation directory not found${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Downloaded Blacksmith"

# Install based on method
echo ""
echo -e "${BLUE}Installing Blacksmith (method: ${INSTALL_METHOD})...${NC}"

case "${INSTALL_METHOD}" in
    venv)
        echo "Creating virtual environment..."
        VENV_PATH="${HOME}/.blacksmith-venv"
        
        # Check if venv already exists
        if [ -d "${VENV_PATH}" ]; then
            echo -e "${YELLOW}⚠${NC} Virtual environment already exists at ${VENV_PATH}"
            echo "Removing old virtual environment..."
            rm -rf "${VENV_PATH}"
        fi
        
        # Create venv
        ${PYTHON_CMD} -m venv "${VENV_PATH}"
        if [ $? -ne 0 ]; then
            echo -e "${RED}✗${NC} Failed to create virtual environment"
            exit 1
        fi
        
        # Activate venv and install
        source "${VENV_PATH}/bin/activate"
        python -m pip install --upgrade pip
        python -m pip install -e "${INSTALL_DIR}"
        
        echo -e "${GREEN}✓${NC} Blacksmith installed in virtual environment"
        echo ""
        echo -e "${YELLOW}To use Blacksmith, activate the virtual environment:${NC}"
        echo -e "${BLUE}  source ${VENV_PATH}/bin/activate${NC}"
        echo ""
        echo -e "${YELLOW}Or create an alias in your shell profile (~/.bashrc or ~/.zshrc):${NC}"
        echo -e "${BLUE}  alias blacksmith=\"${VENV_PATH}/bin/blacksmith\"${NC}"
        echo ""
        echo -e "${YELLOW}To activate automatically, add this to your shell profile:${NC}"
        echo -e "${BLUE}  export BLACKSMITH_VENV=\"${VENV_PATH}\"${NC}"
        echo -e "${BLUE}  [ -f \"\${BLACKSMITH_VENV}/bin/activate\" ] && source \"\${BLACKSMITH_VENV}/bin/activate\"${NC}"
        ;;
    user)
        echo "Installing for current user..."
        ${PYTHON_CMD} -m pip install --upgrade pip
        ${PYTHON_CMD} -m pip install --user -e "${INSTALL_DIR}"
        echo -e "${GREEN}✓${NC} Blacksmith installed for current user"
        ;;
    global)
        echo "Installing globally (may require sudo)..."
        ${PYTHON_CMD} -m pip install --upgrade pip
        if [ "$EUID" -eq 0 ]; then
            ${PYTHON_CMD} -m pip install -e "${INSTALL_DIR}"
        else
            sudo ${PYTHON_CMD} -m pip install -e "${INSTALL_DIR}"
        fi
        echo -e "${GREEN}✓${NC} Blacksmith installed globally"
        ;;
    *)
        echo -e "${RED}✗ Unknown install method: ${INSTALL_METHOD}${NC}"
        echo "Valid methods: global, venv, user"
        exit 1
        ;;
esac

# Verify installation
echo ""
if command -v blacksmith &> /dev/null; then
    echo -e "${GREEN}✓${NC} Blacksmith is now installed!"
    echo ""
    echo "You can now use Blacksmith:"
    echo "  blacksmith              # Interactive menu"
    echo "  blacksmith list         # List available sets"
    echo "  blacksmith install <set>  # Install a set"
    echo ""
    echo "To uninstall, run:"
    echo "  blacksmith uninstall"
    echo "  # or use the uninstall.sh script"
else
    echo -e "${YELLOW}⚠${NC} Blacksmith installed but command not found in PATH"
    if [ "${INSTALL_METHOD}" = "user" ]; then
        echo "You may need to add ~/.local/bin to your PATH"
        echo "Add this to your ~/.bashrc or ~/.zshrc:"
        echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    fi
fi

