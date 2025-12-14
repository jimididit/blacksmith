#!/bin/bash

# Blacksmith Uninstallation Script

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔨 Blacksmith Uninstallation Script${NC}"
echo ""

# Check if blacksmith is installed
if ! command -v blacksmith &> /dev/null; then
    echo -e "${YELLOW}⚠${NC} Blacksmith does not appear to be installed."
    exit 0
fi

echo -e "${GREEN}✓${NC} Found Blacksmith installation"

# Find pip command
PIP_CMD="pip3"
if ! command -v pip3 &> /dev/null; then
    PIP_CMD="pip"
fi

if ! command -v ${PIP_CMD} &> /dev/null; then
    echo -e "${RED}✗${NC} pip not found. Cannot uninstall automatically."
    exit 1
fi

# Confirm uninstallation
echo ""
read -p "Are you sure you want to uninstall Blacksmith? (y/N): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Uninstallation cancelled.${NC}"
    exit 0
fi

echo ""
echo -e "${BLUE}Uninstalling Blacksmith...${NC}"

# Try different uninstall methods
SUCCESS=false

# Method 1: pip uninstall
if ${PIP_CMD} show blacksmith &> /dev/null; then
    echo "Attempting uninstall with ${PIP_CMD}..."
    if ${PIP_CMD} uninstall -y blacksmith 2>/dev/null; then
        SUCCESS=true
    fi
fi

# Method 2: pip uninstall --user
if [ "$SUCCESS" = false ]; then
    echo "Attempting uninstall with ${PIP_CMD} --user..."
    if ${PIP_CMD} uninstall -y --user blacksmith 2>/dev/null; then
        SUCCESS=true
    fi
fi

# Method 3: Try with sudo if needed
if [ "$SUCCESS" = false ] && [ "$EUID" -ne 0 ]; then
    echo "Attempting uninstall with sudo..."
    if sudo ${PIP_CMD} uninstall -y blacksmith 2>/dev/null; then
        SUCCESS=true
    fi
fi

# Verify uninstallation
if command -v blacksmith &> /dev/null; then
    echo -e "${YELLOW}⚠${NC} Blacksmith command still found. Manual removal may be required."
    echo "Try running:"
    echo "  ${PIP_CMD} uninstall blacksmith"
    echo "  ${PIP_CMD} uninstall --user blacksmith"
    exit 1
elif [ "$SUCCESS" = true ]; then
    echo -e "${GREEN}✓${NC} Blacksmith uninstalled successfully!"
    exit 0
else
    echo -e "${RED}✗${NC} Could not automatically uninstall Blacksmith."
    echo "Please try manually:"
    echo "  ${PIP_CMD} uninstall blacksmith"
    echo "  ${PIP_CMD} uninstall --user blacksmith"
    exit 1
fi

