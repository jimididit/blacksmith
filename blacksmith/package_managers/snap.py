"""Snap package manager implementation."""

import subprocess
from typing import List

from blacksmith.package_managers.base import PackageManager
from blacksmith.utils.logger import setup_logger

logger = setup_logger(__name__)


class SnapManager(PackageManager):
    """Snap package manager for Linux."""
    
    def __init__(self):
        super().__init__("snap")
    
    def is_available(self) -> bool:
        """Check if snap is available."""
        try:
            result = subprocess.run(
                ["snap", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def install(self, packages: List[str]) -> bool:
        """Install packages using snap."""
        if not packages:
            return True
        
        try:
            # Don't capture output so sudo password prompts are visible
            success = True
            for package in packages:
                cmd = ["sudo", "snap", "install", package]
                result = subprocess.run(
                    cmd,
                    timeout=600
                )
                if result.returncode != 0:
                    logger.error(f"Snap install failed for {package}")
                    success = False
            return success
        except subprocess.TimeoutExpired:
            logger.error("Snap install timed out")
            return False
    
    def is_installed(self, package: str) -> bool:
        """Check if package is installed."""
        try:
            result = subprocess.run(
                ["snap", "list", package],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0 and package in result.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def update_package(self, package: str) -> bool:
        """Update a specific package using snap refresh."""
        try:
            cmd = ["sudo", "snap", "refresh", package]
            result = subprocess.run(
                cmd,
                timeout=600
            )
            if result.returncode != 0:
                logger.error(f"Snap refresh failed for {package}")
                from blacksmith.utils.ui import print_error
                print_error(f"Failed to update {package}")
                return False
            return True
        except subprocess.TimeoutExpired:
            logger.error("Snap refresh timed out")
            from blacksmith.utils.ui import print_error
            print_error("Snap refresh timed out")
            return False

