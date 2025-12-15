"""Flatpak package manager implementation."""

import subprocess
from typing import List

from blacksmith.package_managers.base import PackageManager
from blacksmith.utils.logger import setup_logger

logger = setup_logger(__name__)


class FlatpakManager(PackageManager):
    """Flatpak package manager for Linux."""
    
    def __init__(self):
        super().__init__("flatpak")
    
    def is_available(self) -> bool:
        """Check if flatpak is available."""
        try:
            result = subprocess.run(
                ["flatpak", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def install(self, packages: List[str]) -> bool:
        """Install packages using flatpak."""
        if not packages:
            return True
        
        try:
            success = True
            for package in packages:
                cmd = ["flatpak", "install", "-y", "flathub", package]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=600
                )
                if result.returncode != 0:
                    logger.error(f"Flatpak install failed for {package}: {result.stderr}")
                    success = False
            return success
        except subprocess.TimeoutExpired:
            logger.error("Flatpak install timed out")
            return False
    
    def is_installed(self, package: str) -> bool:
        """Check if package is installed."""
        try:
            result = subprocess.run(
                ["flatpak", "list", "--app", "--columns=application"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0 and package in result.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def update_package(self, package: str) -> bool:
        """Update a specific package using flatpak update."""
        try:
            cmd = ["flatpak", "update", "-y", package]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600
            )
            if result.returncode != 0:
                error_msg = result.stderr.strip() or result.stdout.strip()
                logger.error(f"Flatpak update failed for {package}: {error_msg}")
                from blacksmith.utils.ui import print_error
                if "already installed" in error_msg.lower() or "up to date" in error_msg.lower():
                    print_error(f"{package} is already up to date")
                else:
                    print_error(f"Failed to update {package}: {error_msg[:150]}")
                return False
            return True
        except subprocess.TimeoutExpired:
            logger.error("Flatpak update timed out")
            from blacksmith.utils.ui import print_error
            print_error("Flatpak update timed out")
            return False

